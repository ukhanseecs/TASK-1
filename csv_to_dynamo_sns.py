import boto3
import csv
import json
import os
import uuid
from datetime import datetime
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS Configuration from environment variables
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
DYNAMODB_TABLE_NAME = os.getenv('DYNAMODB_TABLE_NAME')
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
USE_OPENAI_BY_DEFAULT = os.getenv('USE_OPENAI_BY_DEFAULT', 'False').lower() == 'true'

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
sns_client = boto3.client('sns', region_name=AWS_REGION)

# Configure OpenAI (if API key is provided)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

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
    
    # Optional: Add some basic statistics if the data is numeric
    # This is a simplified example - extend as needed for your specific data
    return summary

def generate_openai_summary(data):
    """Generate a summary using OpenAI (optional)"""
    if not data or not openai.api_key:
        return "OpenAI summary not available."
    
    try:
        # Convert data to string format that OpenAI can process
        data_sample = data[:5]  # Just use a sample to keep request size manageable
        data_str = json.dumps(data_sample, indent=2)
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data analyst summarizing CSV data."},
                {"role": "user", "content": f"Please provide a concise summary of this CSV data. Here's a sample: {data_str}"}
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

def store_in_dynamodb(data, summary):
    """Store data and summary in DynamoDB"""
    try:
        # Create an entry for the overall dataset with summary
        timestamp = datetime.now().isoformat()
        item_id = str(uuid.uuid4())
        
        main_item = {
            'id': item_id,
            'timestamp': timestamp,
            'record_count': len(data),
            'summary': json.dumps(summary),
            'type': 'dataset_summary'
        }
        
        # Store the main summary item
        table.put_item(Item=main_item)
        print(f"Stored dataset summary with ID: {item_id}")
        
        # Store individual records (optional - comment out if not needed)
        for i, record in enumerate(data):
            record_id = f"{item_id}_record_{i}"
            record_item = {
                'id': record_id,
                'parent_id': item_id,
                'timestamp': timestamp,
                'data': json.dumps(record),
                'type': 'record'
            }
            table.put_item(Item=record_item)
        
        print(f"Stored {len(data)} individual records in DynamoDB")
        return item_id
    except Exception as e:
        print(f"Error storing data in DynamoDB: {e}")
        return None

def publish_sns_event(item_id, summary):
    """Publish an SNS notification about the processed data"""
    try:
        message = {
            'event_type': 'csv_processed',
            'timestamp': datetime.now().isoformat(),
            'item_id': item_id,
            'record_count': summary.get('record_count', 0),
            'summary_type': summary.get('summary_type', 'unknown')
        }
        
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message),
            Subject='CSV Processing Completed'
        )
        
        print(f"Published SNS event: MessageId = {response['MessageId']}")
        return True
    except Exception as e:
        print(f"Error publishing SNS event: {e}")
        return False

def main():
    """Main function to orchestrate the data processing workflow"""
    # Check if required environment variables are set
    if not DYNAMODB_TABLE_NAME:
        print("Error: DYNAMODB_TABLE_NAME is not set in the .env file")
        return
    
    if not SNS_TOPIC_ARN:
        print("Error: SNS_TOPIC_ARN is not set in the .env file")
        return
    
    # Get CSV file path
    csv_file_path = input("Enter the path to your CSV file: ")
    
    if not os.path.exists(csv_file_path):
        print(f"Error: File not found at {csv_file_path}")
        return
    
    # Read CSV data
    data = read_csv_file(csv_file_path)
    if not data:
        print("Failed to read CSV data. Exiting.")
        return
    
    # Generate summaries
    manual_summary = generate_manual_summary(data)
    
    # Choose summary type based on environment variable or user input
    use_openai = USE_OPENAI_BY_DEFAULT
    
    if not USE_OPENAI_BY_DEFAULT:
        use_openai = input("Would you like to use OpenAI for summary generation? (yes/no): ").lower() == 'yes'
    
    if use_openai:
        if not OPENAI_API_KEY:
            print("Warning: OpenAI API Key is not set in .env file. Using manual summary instead.")
            summary = manual_summary
        else:
            summary = generate_openai_summary(data)
    else:
        summary = manual_summary
    
    # Store in DynamoDB
    item_id = store_in_dynamodb(data, summary)
    if not item_id:
        print("Failed to store data in DynamoDB. Exiting.")
        return
    
    # Publish SNS event
    published = publish_sns_event(item_id, summary)
    if published:
        print("Process completed successfully!")
    else:
        print("Process completed but failed to publish SNS event.")

if __name__ == "__main__":
    main()