# FastAPI PII Data Anonymization Service

![FastAPI Logo](https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png)

This repository contains a FastAPI service that utilizes the `presidio_anonymizer` package to remove Personally Identifiable Information (PII) data from JSON input. This is particularly useful for anonymizing sensitive information in text data before storage or analysis.

## Installation

To set up and run this FastAPI service, follow these steps:

1. Clone this repository to your local machine:

   ```bash
   git clone https://github.com/omers/pii-anonymizer-api.git
   ```

2. Navigate to the project directory:

   ```bash
   cd pii-anonymizer-api
   ```

3. Create a virtual environment (recommended) and activate it:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the FastAPI service:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

   The service will start and listen on http://localhost:8000.

2. Make a POST request to the `/anonymize` endpoint with JSON data containing the text to be anonymized:

   ```json
   {
       "text": "John Doe's email is john@example.com and his phone number is 555-1234."
   }
   ```

   You can use tools like `curl` or Postman to send POST requests to the endpoint.

3. The service will respond with the anonymized text:

   ```json
   {
       "text": "[PII_EMAIL] email is [PII_EMAIL] and his phone number is [PII_PHONE_US]."
   }
   ```

## Configuration

You can modify the behavior of the anonymization process by editing the `config.json` file. The available configuration options can be found in the `presidio_anonymizer` documentation.

## Contributing

Contributions to this project are welcome! If you encounter issues or have suggestions for improvements, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).

---

**Note:** This readme is a template and may need to be customized based on your project's actual structure and requirements. Make sure to replace placeholders (e.g., `[PII_EMAIL]`, `[PII_PHONE_US]`, `your-username`, etc.) with actual values and information specific to your project.
