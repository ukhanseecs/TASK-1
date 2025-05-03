# CSV to DynamoDB with SNS Notifications

A secure Python utility for processing CSV files containing purchase transaction data, storing the data in Amazon DynamoDB, and sending notifications through Amazon SNS.

## Features

- **CSV Data Processing**: Reads purchase transaction data from CSV files.
- **Data Validation**: Validates that required fields are present in the CSV file.
- **AI-Powered Summaries**: Optional integration with Groq or OpenAI to generate intelligent summaries of purchase data.
- **Secure Credential Handling**: Multiple secure options for handling API credentials.
- **DynamoDB Storage**: Stores both individual records and a summary in Amazon DynamoDB.
- **SNS Notifications**: Sends event notifications when processing is complete.

## Prerequisites

- Python 3.10 or higher
- AWS account with appropriate permissions for DynamoDB and SNS
- Groq API key and/or OpenAI API key (optional, for AI summaries)

## Installation

1. Clone this repository or download the source code.
2. Create a virtual environment and activate it:
```bash
python -m venv env
# On Windows
env\Scripts\activate
# On Linux/Mac
source env/bin/activate
```
3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example `.env` file and update it with your settings:
```
# AWS Configuration
AWS_REGION=your-aws-region
DYNAMODB_TABLE_NAME=your-dynamodb-table
SNS_TOPIC_ARN=your-sns-topic-arn

# API Configuration (do not store in .env for production)
GROQ_API_KEY=
OPENAI_API_KEY=

# Security configuration
USE_SECRETS_MANAGER=False

# Summary options
USE_AI_BY_DEFAULT=False
AI_PROVIDER=groq
```

### Security Options

This application supports multiple approaches for securely handling API keys:

1. **Environment Variables**: Set the API keys as environment variables before running the script
2. **AWS Secrets Manager**: Store your API keys in AWS Secrets Manager and set `USE_SECRETS_MANAGER=True`
3. **Manual Input**: Leave the API keys blank and manually provide them when prompted

For production use, **never** store API keys directly in the `.env` file.

## Usage

1. Ensure your CSV file has the expected column format (see below)
2. Activate your virtual environment
3. Run the script:
```bash
python csv_to_dynamo_sns.py
```
4. Follow the prompts to select your CSV file and processing options

### Expected CSV Format

The CSV file should include these fields (missing fields will trigger a warning):
- summary_id: Unique identifier for each transaction
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

## AI Summary Generation

When enabled, the application can use either Groq or OpenAI to generate intelligent summaries of your purchase data. To use this feature:

1. Obtain an API key from [Groq](https://console.groq.com/) or [OpenAI](https://platform.openai.com/)
2. Set the key securely using one of the security options mentioned above
3. Set `AI_PROVIDER` to either "groq" or "openai" in your configuration
4. Set `USE_AI_BY_DEFAULT` to "True" to always use AI, or respond to the prompt during execution

## AWS Resources

The application requires the following AWS resources:

1. A DynamoDB table with a partition key named "summary_id"
2. An SNS topic for notifications
3. (Optional) Secrets in AWS Secrets Manager if using that security option

Make sure your AWS credentials have appropriate permissions to access these resources.

## License

[MIT License](LICENSE)