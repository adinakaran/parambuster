# Web Parameter Finder

A Python tool that discovers various types of parameters in web applications by analyzing HTML source code, including query parameters, form inputs, JavaScript variables, and comments.

## Features

- Extracts parameters from multiple sources:
  - URL query strings
  - HTML forms (both visible and hidden inputs)
  - JavaScript code (variable assignments and object keys)
  - HTML comments
  - Potential path/route parameters
- Heuristic analysis for path parameters and JavaScript variables
- Clear categorization of found parameters
- Simple command-line interface

## Installation

1. Ensure you have Python 3.6+ installed
2. Install dependencies:
```bash
pip install -r requirements.txt
```
Usage
```bash
python parameter_finder.py <URL>
```
Example
```bash
python parameter_finder.py https://example.com/search?q=test
```
Output
The tool provides categorized output showing parameters found in different contexts:

text
--- URL Query Parameters (1 found) ---
  - q

--- Potential Path/Route Parameters (3 found) ---
  - user_id
  - product_slug
  - id

--- Form Parameters (Visible) (2 found) ---
  - username
  - password

--- Form Parameters (Hidden) (1 found) ---
  - csrf_token

--- JavaScript-like Parameters (4 found) ---
  - apiKey
  - userId
  - sessionToken
  - config

--- Comment Parameters (2 found) ---
  - debug_mode
  - admin_flag
Parameter Types Explained
URL Query Parameters: Parameters found in the URL's query string

Potential Path/Route Parameters: Parameters identified in URL paths using heuristics

Form Parameters (Visible): Input fields in HTML forms (text, select, etc.)

Form Parameters (Hidden): Hidden input fields in forms

JavaScript-like Parameters: Variables and object keys found in script tags

Comment Parameters: Potential parameters mentioned in HTML comments

Notes
Path/Route parameters are identified heuristically and may include false positives

JavaScript analysis is static and may not catch all dynamically generated parameters

For client-side rendered applications, consider using browser automation tools

Always use this tool ethically and with proper authorization

License
MIT License - Use responsibly.

text

The `requirements.txt` includes only the essential dependencies needed to run the script. The README provides clear instructions, examples, and explanations of the different parameter types the tool can discover. The documentation emphasizes the heuristic nature of some findings and includes important ethical considerations.
