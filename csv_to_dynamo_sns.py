import boto3
import csv
import json
import os
import uuid
from datetime import datetime
import groq
from dotenv import load_dotenv
from decimal import Decimal  # Add import for Decimal type

# Load environment variables from .env file
load_dotenv()

# AWS Configuration from environment variables
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')

# AI API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# AI configuration
USE_AI_BY_DEFAULT = os.getenv('USE_AI_BY_DEFAULT', 'False').lower() == 'true'
AI_PROVIDER = os.getenv('AI_PROVIDER', 'groq').lower()

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
sns_client = boto3.client('sns', region_name=AWS_REGION)

# Configure OpenAI client (if API key is provided)
openai_client = None
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    openai_client = openai

# Configure Groq client (if API key is provided)
groq_client = None
if GROQ_API_KEY:
    groq_client = groq.Groq(api_key=GROQ_API_KEY)

def read_csv_file(file_path):
    """Read data from CSV file and return as list of dictionaries"""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                data.append(dict(row))
        print(f"Successfully read {len(data)} rows from {file_path}")
        return data
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def generate_manual_summary(data):
    """Generate a simple summary of the CSV data manually"""
    if not data:
        return "No data available to summarize."
    
    # Number of records
    num_records = len(data)
    
    # Get column names
    columns = list(data[0].keys())
    
    # Create summary
    summary = {
        "record_count": num_records,
        "columns": columns,
        "generated_at": datetime.now().isoformat(),
        "summary_type": "manual"
    }
    
    return summary

def generate_groq_summary(data):
    """Generate a summary using Groq API focusing on purchase data"""
    if not data or not groq_client:
        return "Groq summary not available."
    
    try:
        # Convert data to string format that Groq can process
        data_sample = data[:5]  # Just use a sample to keep request size manageable
        data_str = json.dumps(data_sample, indent=2)
        
        prompt = f"""
        The data represents purchase transactions with the following fields:
        - summary_id: Unique identifier for each transaction (partition key)
        - department: Department making the purchase
        - cost_center: Cost center associated with the purchase
        - requester: Person requesting the purchase
        - approval_status: Current approval status
        - approved_by: Person who approved the transaction
        - vendor: Vendor/supplier name
        - item: Item being purchased
        - category: Category of the purchase
        - cost_usd: Cost in USD
        - currency: Currency used
        - purchase_date: Date of purchase
        - delivery_date: Expected delivery date
        - payment_method: Method of payment
        - priority: Priority level
        - tags: Associated tags
        - notes: Additional notes
        
        Please analyze this sample data and provide a concise business summary:
        {data_str}
        """
        
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",  # Using LLaMA 3 model
            messages=[
                {"role": "system", "content": "You are a procurement analyst summarizing purchase transaction data."},
                {"role": "user", "content": prompt}
            ]
        )
        
        summary = {
            "record_count": len(data),
            "summary": response.choices[0].message.content,
            "generated_at": datetime.now().isoformat(),
            "summary_type": "groq"
        }
        return summary
    except Exception as e:
        print(f"Error generating Groq summary: {e}")
        return {"error": str(e), "summary_type": "groq_failed"}

def generate_openai_summary(data):
    """Generate a summary using OpenAI for purchase transaction data"""
    if not data or not openai_client:
        return "OpenAI summary not available."
    
    try:
        # Convert data to string format that OpenAI can process
        data_sample = data[:5]  # Just use a sample to keep request size manageable
        data_str = json.dumps(data_sample, indent=2)
        
        prompt = f"""
        The data represents purchase transactions with the following fields:
        - summary_id: Unique identifier for each transaction (partition key)
        - department: Department making the purchase
        - cost_center: Cost center associated with the purchase
        - requester: Person requesting the purchase
        - approval_status: Current approval status
        - approved_by: Person who approved the transaction
        - vendor: Vendor/supplier name
        - item: Item being purchased
        - category: Category of the purchase
        - cost_usd: Cost in USD
        - currency: Currency used
        - purchase_date: Date of purchase
        - delivery_date: Expected delivery date
        - payment_method: Method of payment
        - priority: Priority level
        - tags: Associated tags
        - notes: Additional notes
        
        Please analyze this sample data and provide a concise business summary:
        {data_str}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a procurement analyst summarizing purchase transaction data."},
                {"role": "user", "content": prompt}
            ]
        )
        
        summary = {
            "record_count": len(data),
            "summary": response.choices[0].message['content'],
            "generated_at": datetime.now().isoformat(),
            "summary_type": "openai"
        }
        return summary
    except Exception as e:
        print(f"Error generating OpenAI summary: {e}")
        return {"error": str(e), "summary_type": "openai_failed"}

def generate_ai_summary(data, provider=None):
    """Generate a summary using the specified AI provider"""
    if provider is None:
        provider = AI_PROVIDER
        
    if provider == "groq" and groq_client:
        return generate_groq_summary(data)
    elif provider == "openai" and openai_client:
        return generate_openai_summary(data)
    else:
        return {"error": f"No valid API key found for {provider}", "summary_type": "ai_failed"}

def store_in_dynamodb(data, summary):
    """Store data and summary in DynamoDB"""
    try:
        # Create an entry for the overall dataset with summary
        timestamp = datetime.now().isoformat()
        summary_id = str(uuid.uuid4())
        
        main_item = {
            'summary_id': summary_id,  # Using summary_id as the partition key
            'timestamp': timestamp,
            'record_count': len(data),
            'summary': json.dumps(summary),
            'type': 'dataset_summary'
        }
        
        # Store the main summary item
        table.put_item(Item=main_item)
        print(f"Stored dataset summary with summary_id: {summary_id}")
        
        # Store individual records
        for record in data:
            # Check if record already has a summary_id, otherwise generate one
            if 'summary_id' not in record or not record['summary_id']:
                record['summary_id'] = str(uuid.uuid4())
                
            # Convert numeric fields to Decimal type for DynamoDB compatibility
            if 'cost_usd' in record and record['cost_usd']:
                try:
                    record['cost_usd'] = Decimal(str(record['cost_usd']))  # Convert to Decimal via string to avoid precision issues
                except (ValueError, TypeError):
                    pass  # Keep as string if conversion fails
            
            # Add timestamp for when this record was processed
            record['processed_timestamp'] = timestamp
            
            # Put the record in DynamoDB
            table.put_item(Item=record)
        
        print(f"Stored {len(data)} individual purchase records in DynamoDB")
        return summary_id
    except Exception as e:
        print(f"Error storing data in DynamoDB: {e}")
        return None

def publish_sns_event(summary_id, summary):
    """Publish an SNS notification about the processed purchase data"""
    try:
        message = {
            'event_type': 'purchase_data_processed',
            'timestamp': datetime.now().isoformat(),
            'summary_id': summary_id,
            'record_count': summary.get('record_count', 0),
            'summary_type': summary.get('summary_type', 'unknown'),
            'processed_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message),
            Subject='Purchase Data Processing Completed'
        )
        
        print(f"Published SNS event: MessageId = {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Error publishing SNS event: {e}")
        return False

def main():
    """Main function to orchestrate the purchase data processing workflow"""
    # Check if required environment variables are set
    if not DYNAMODB_TABLE_NAME:
        print("Error: DYNAMODB_TABLE_NAME is not set in the .env file")
        return
    
    if not SNS_TOPIC_ARN:
        print("Error: SNS_TOPIC_ARN is not set in the .env file")
        return
    
    # Get CSV file path - default to 'csv/data.csv' if available
    default_path = os.path.join('csv', 'data.csv')
    if os.path.exists(default_path):
        csv_file_path = input(f"Enter the path to your CSV file (default: {default_path}): ") or default_path
    else:
        csv_file_path = input("Enter the path to your CSV file: ")
    
    if not os.path.exists(csv_file_path):
        print(f"Error: File not found at {csv_file_path}")
        return
    
    # Read CSV data
    data = read_csv_file(csv_file_path)
    if not data:
        print("Failed to read CSV data. Exiting.")
        return
    
    # Validate that the CSV has the required fields
    expected_fields = [
        'summary_id', 'department', 'cost_center', 'requester', 'approval_status', 
        'approved_by', 'vendor', 'item', 'category', 'cost_usd', 'currency', 
        'purchase_date', 'delivery_date', 'payment_method', 'priority', 'tags', 'notes'
    ]
    
    # Check if all expected fields are in the data
    first_row_keys = list(data[0].keys())
    missing_fields = [field for field in expected_fields if field not in first_row_keys]
    
    if missing_fields:
        print(f"Warning: The following expected fields are missing from the CSV: {missing_fields}")
        proceed = input("Do you want to proceed anyway? (yes/no): ").lower() == 'yes'
        if not proceed:
            print("Exiting as requested.")
            return
    
    # Generate manual summary
    manual_summary = generate_manual_summary(data)
    
    # Determine if we should use AI for summary
    use_ai = USE_AI_BY_DEFAULT
    
    if not USE_AI_BY_DEFAULT:
        use_ai = input("Would you like to use AI for summary generation? (yes/no): ").lower() == 'yes'
    
    if use_ai:
        # Determine which AI provider to use
        provider = AI_PROVIDER
        if provider not in ["groq", "openai"]:
            print(f"Warning: Invalid AI provider '{provider}' in .env file. Using Groq as default.")
            provider = "groq"
            
        if provider == "groq" and not GROQ_API_KEY:
            print("Warning: Groq API Key is not set in .env file. Using manual summary instead.")
            summary = manual_summary
        elif provider == "openai" and not OPENAI_API_KEY:
            print("Warning: OpenAI API Key is not set in .env file. Using manual summary instead.")
            summary = manual_summary
        else:
            print(f"Generating summary using {provider.capitalize()}...")
            summary = generate_ai_summary(data, provider)
    else:
        summary = manual_summary
    
    # Store in DynamoDB
    summary_id = store_in_dynamodb(data, summary)
    if not summary_id:
        print("Failed to store data in DynamoDB. Exiting.")
        return
    
    # Publish SNS event
    published = publish_sns_event(summary_id, summary)
    if published:
        print("Purchase data processing completed successfully!")
    else:
        print("Process completed but failed to publish SNS event.")

if __name__ == "__main__":
    main()