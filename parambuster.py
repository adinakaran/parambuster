import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, parse_qs, urljoin
import re
import sys

class WebParameterFinder:
    """
    A class to find public and hidden parameters in a web application's HTML source,
    including query string, form, JavaScript, comments, and potential path parameters.
    """

    def __init__(self, url):
        self.url = url
        self.html_content = None
        self.found_parameters = {
            "URL Query Parameters": set(),
            "Potential Path/Route Parameters": set(),
            "Form Parameters (Visible)": set(),
            "Form Parameters (Hidden)": set(),
            "JavaScript-like Parameters": set(),
            "Comment Parameters": set(),
        }
        self.processed_urls = set() # To avoid redundant processing of URLs

    def fetch_page(self):
        """
        Fetches the HTML content of the given URL.
        """
        try:
            print(f"[*] Fetching page: {self.url}")
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            self.html_content = response.text
            print("[*] Page fetched successfully.")
        except requests.exceptions.RequestException as e:
            print(f"[-] Error fetching page {self.url}: {e}")
            sys.exit(1) # Exit if we can't fetch the page

    def extract_url_query_parameters(self):
        """
        Extracts parameters directly from the URL's query string.
        """
        parsed_url = urlparse(self.url)
        query_params = parse_qs(parsed_url.query)
        for param_name in query_params.keys():
            self.found_parameters["URL Query Parameters"].add(param_name)
        if query_params:
            print(f"[+] Found URL Query Parameters: {list(query_params.keys())}")
        else:
            print("[-] No URL Query Parameters found in the initial URL.")

    def extract_potential_path_parameters(self):
        """
        Extracts potential path/route parameters by analyzing URLs found in the HTML.
        This uses heuristics to identify dynamic segments or explicit placeholders.
        """
        if not self.html_content:
            return

        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        # Collect all potential URLs from href, action, and script tags
        urls_to_analyze = set()

        # From <a> tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            urls_to_analyze.add(urljoin(self.url, href)) # Resolve relative URLs

        # From <form> tags
        for form_tag in soup.find_all('form', action=True):
            action = form_tag['action']
            urls_to_analyze.add(urljoin(self.url, action)) # Resolve relative URLs

        # From <script> tags (look for URL-like strings)
        script_content = "\n".join([script.string if script.string else '' for script in soup.find_all('script')])
        # A more general regex for URLs in scripts, including relative paths
        # This is a broad net and might catch non-URL strings.
        js_url_pattern = re.compile(r'(?:["\'])(/?[a-zA-Z0-9_\-./]+)(?:["\'])')
        for match in js_url_pattern.finditer(script_content):
            found_url = match.group(1)
            # Filter out very short or clearly non-URL strings
            if len(found_url) > 2 and not found_url.startswith('//'): # Exclude protocol relative URLs and very short ones
                urls_to_analyze.add(urljoin(self.url, found_url))
        
        potential_path_params = set()
        print("[*] Analyzing URLs for potential path parameters...")

        for url_str in urls_to_analyze:
            if url_str in self.processed_urls:
                continue
            self.processed_urls.add(url_str) # Mark as processed

            parsed_url = urlparse(url_str)
            path_segments = [s for s in parsed_url.path.split('/') if s] # Split and remove empty strings

            if not path_segments:
                continue

            for i, segment in enumerate(path_segments):
                # Heuristic 1: Explicit placeholders (e.g., {id}, :slug)
                explicit_placeholder_match = re.match(r'[{:]?([a-zA-Z_$][a-zA-Z0-9_$]*)[}]?', segment)
                if explicit_placeholder_match and explicit_placeholder_match.group(1) != segment: # Ensure it's not just a regular word
                    potential_path_params.add(explicit_placeholder_match.group(1))
                    print(f"    [+] Found explicit path placeholder: {explicit_placeholder_match.group(1)} in {url_str}")
                
                # Heuristic 2: Numeric IDs (e.g., /users/123, where 123 is the segment)
                if segment.isdigit() and len(segment) > 1: # Avoid single digits unless context suggests
                    # If the previous segment is known (e.g., 'users', 'products'),
                    # we can infer a parameter name. Otherwise, it's just 'id' or 'numeric_param'.
                    param_name_hint = "id"
                    if i > 0:
                        prev_segment = path_segments[i-1].lower()
                        if prev_segment in ["users", "products", "items", "posts", "orders"]:
                            param_name_hint = f"{prev_segment}_id"
                        elif prev_segment.endswith('s'): # plural like "categories"
                            param_name_hint = f"{prev_segment[:-1]}_id"
                    
                    potential_path_params.add(param_name_hint)
                    print(f"    [+] Found numeric path segment (potential {param_name_hint}): {segment} in {url_str}")

                # Heuristic 3: Common slug patterns (e.g., "my-product-title", "john-doe")
                # Exclude common fixed path segments like "api", "v1", "css", "js", "img"
                common_static_segments = {"api", "v1", "v2", "css", "js", "img", "images", "static", "assets", "admin", "dashboard", "new", "edit", "delete", "view", "index", "home"}
                if (re.match(r'^[a-zA-Z0-9_-]+$', segment) and
                    not segment.isdigit() and # Already covered by Heuristic 2
                    len(segment) > 2 and # Avoid very short segments like 'a', 'b'
                    segment.lower() not in common_static_segments):
                    
                    # This is highly heuristic. Could be a file name, or a slug.
                    # We'll just add "slug" or "name" as a generic placeholder.
                    param_name_hint = "slug"
                    if i > 0:
                        prev_segment = path_segments[i-1].lower()
                        if prev_segment in ["products", "articles", "posts", "categories", "users"]:
                            param_name_hint = f"{prev_segment[:-1]}_slug" if prev_segment.endswith('s') else f"{prev_segment}_name"
                    
                    potential_path_params.add(param_name_hint)
                    print(f"    [+] Found alphanumeric/hyphenated path segment (potential {param_name_hint}): {segment} in {url_str}")

        if potential_path_params:
            print(f"[+] Potential Path/Route Parameters found: {list(potential_path_params)}")
            self.found_parameters["Potential Path/Route Parameters"].update(potential_path_params)
        else:
            print("[-] No potential Path/Route Parameters found from URLs on the page.")


    def extract_form_parameters(self):
        """
        Extracts parameters from HTML forms (input, select, textarea elements).
        Separates visible and hidden inputs.
        """
        if not self.html_content:
            return

        soup = BeautifulSoup(self.html_content, 'html.parser')
        forms = soup.find_all('form')
        
        if not forms:
            print("[-] No forms found on the page.")
            return

        for i, form in enumerate(forms):
            print(f"[*] Analyzing Form {i+1} (Action: {form.get('action', 'N/A')}, Method: {form.get('method', 'GET')})")
            
            # Find all relevant input elements within the form
            form_elements = form.find_all(['input', 'select', 'textarea'])
            
            for element in form_elements:
                name = element.get('name')
                if name:
                    if element.name == 'input' and element.get('type') == 'hidden':
                        self.found_parameters["Form Parameters (Hidden)"].add(name)
                        print(f"    [+] Hidden Form Parameter: {name}")
                    else:
                        # Corrected line: removed the extra '()' after "Form Parameters (Visible)"
                        self.found_parameters["Form Parameters (Visible)"].add(name)
                        print(f"    [+] Visible Form Parameter: {name} (Type: {element.get('type', 'text') if element.name == 'input' else element.name})")

    def extract_js_parameters(self):
        """
        Attempts to extract potential parameters from JavaScript code
        by looking for common variable assignment patterns or object keys.
        This is a heuristic approach and may have false positives.
        """
        if not self.html_content:
            return

        soup = BeautifulSoup(self.html_content, 'html.parser')
        script_tags = soup.find_all('script')
        
        if not script_tags:
            print("[-] No <script> tags found on the page.")
            return

        js_content = "\n".join([script.string if script.string else '' for script in script_tags])

        # Regex to find variable assignments or object keys that look like parameters
        # e.g., 'paramName = "value"', 'paramName: "value"', 'name="paramName"'
        param_patterns = re.findall(r'(?:var|let|const|\bthis\.)\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=|([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:\s*(?:["\']|\d)', js_content)
        
        found_in_js = set()
        for match in param_patterns:
            if match[0]: # For assignments (var param = ...)
                found_in_js.add(match[0])
            if match[1]: # For object keys (param: ...)
                found_in_js.add(match[1])

        # Also look for 'name=' attributes within script blocks, though less common for JS variables
        name_attributes_in_js = re.findall(r'name=["\']([a-zA-Z_$][a-zA-Z0-9_$]*)["\']', js_content)
        for name in name_attributes_in_js:
            found_in_js.add(name)

        if found_in_js:
            print(f"[+] Potential JavaScript-like parameters found: {list(found_in_js)}")
            self.found_parameters["JavaScript-like Parameters"].update(found_in_js)
        else:
            print("[-] No JavaScript-like parameters found.")

    def extract_comment_parameters(self):
        """
        Extracts potential parameters from HTML comments.
        """
        if not self.html_content:
            return

        soup = BeautifulSoup(self.html_content, 'html.parser')
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        
        if not comments:
            print("[-] No HTML comments found on the page.")
            return

        found_in_comments = set()
        for comment in comments:
            # Look for words that could be parameter names (e.g., 'param_name=value')
            param_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:["\']?[a-zA-Z0-9_.-]+["\']?|\d+)', str(comment))
            for p in param_matches:
                found_in_comments.add(p)
            
            # Also look for standalone words that might be referenced as parameters
            words_in_comment = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', str(comment))
            common_words = {"this", "that", "the", "and", "or", "not", "for", "in", "with", "is", "of", "to", "a", "an", "on", "at", "by", "from", "as", "it", "he", "she", "we", "they", "you", "my", "your", "his", "her", "our", "their", "its", "up", "down", "left", "right", "true", "false", "null", "undefined"} # Expanded filter
            for word in words_in_comment:
                if len(word) > 2 and word.lower() not in common_words:
                    found_in_comments.add(word)

        if found_in_comments:
            print(f"[+] Potential Comment parameters found: {list(found_in_comments)}")
            self.found_parameters["Comment Parameters"].update(found_in_comments)
        else:
            print("[-] No Comment parameters found.")

    def find_all_parameters(self):
        """
        Executes all parameter extraction methods.
        """
        self.fetch_page()
        self.extract_url_query_parameters()
        self.extract_potential_path_parameters() # New method call
        self.extract_form_parameters()
        self.extract_js_parameters()
        self.extract_comment_parameters()
        self.display_results()

    def display_results(self):
        """
        Prints a summary of all found parameters.
        """
        print("\n" + "="*50)
        print("           Parameter Discovery Results           ")
        print("="*50)
        print(f"Target URL: {self.url}\n")

        total_found = 0
        for category, params_set in self.found_parameters.items():
            params_list = sorted(list(params_set)) # Sort for consistent output
            print(f"--- {category} ({len(params_list)} found) ---")
            if params_list:
                for param in params_list:
                    print(f"  - {param}")
                total_found += len(params_list)
            else:
                print("  (None)")
            print() # Add a newline for spacing between categories

        print("="*50)
        print(f"Total Unique Parameters Discovered: {total_found}")
        print("="*50)
        print("\nNote: Path/Route, JavaScript, and Comment parameters are heuristic and may contain false positives due to static analysis limitations.")
        print("Consider dynamic analysis (e.g., using Selenium) for a more complete picture, especially for client-side rendered parameters.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parameter_finder.py <URL>")
        print("Example: python parameter_finder.py https://example.com/search?q=test")
        sys.exit(1)

    target_url = sys.argv[1]
    finder = WebParameterFinder(target_url)
    finder.find_all_parameters()

