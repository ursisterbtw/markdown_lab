import os
import re

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def clean_text(text):
    """Clean up text content."""
    # Remove multiple consecutive empty lines
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
    # Remove trailing whitespace
    text = re.sub(r"\s+$", "", text, flags=re.MULTILINE)
    # Ensure proper spacing around headers
    text = re.sub(r"(#{1,6})\s*(.+)", r"\1 \2", text)
    return text


def format_markdown(content):
    """Apply consistent formatting to markdown content."""
    lines = content.split("\n")
    formatted_lines = []
    in_code_block = False

    for line in lines:
        # Skip empty lines at start of file
        if not formatted_lines and not line.strip():
            continue

        # Handle code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            formatted_lines.append(line.rstrip())
            continue

        if in_code_block:
            formatted_lines.append(line.rstrip())
            continue

        # Format headers
        if line.strip().startswith("#"):
            # Ensure single space after #
            line = re.sub(r"^(#+)\s*", r"\1 ", line)
            # Add blank line before headers (except at start of file)
            if formatted_lines and formatted_lines[-1].strip():
                formatted_lines.append("")
            formatted_lines.append(line.strip())
            formatted_lines.append("")
            continue

        # Format lists
        if re.match(r"^\s*[-*+]\s", line):
            formatted_lines.append(line.rstrip())
            continue

        # Format numbered lists
        if re.match(r"^\s*\d+\.\s", line):
            formatted_lines.append(line.rstrip())
            continue

        # Regular lines
        if line.strip():
            formatted_lines.append(line.strip())
        else:
            # Only add blank line if previous line wasn't blank
            if formatted_lines and formatted_lines[-1].strip():
                formatted_lines.append("")

    # Clean up the final content
    content = "\n".join(formatted_lines)
    content = clean_text(content)
    return content


def scrape_to_markdown(url, output_dir="scraped_mds"):
    """Scrape webpage and convert to formatted markdown."""
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove unwanted elements
        for element in soup.find_all(["script", "style", "nav", "footer"]):
            element.decompose()

        # Convert to markdown
        markdown_content = md(
            str(soup), heading_style="ATX", bullets="-", code_language="python"
        )

        # Format the content
        formatted_content = format_markdown(markdown_content)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Create filename from URL
        filename = url.split("://")[-1].replace("/", "_")
        if not filename.endswith(".md"):
            filename += ".md"
        filepath = os.path.join(output_dir, filename)

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted_content)

        print(f"Successfully scraped: {url} -> {filepath}")

    except requests.RequestException as e:
        print(f"Error scraping {url}: {e!s}")
    except Exception as e:
        print(f"Unexpected error processing {url}: {e!s}")


def main():
    urls = [
        "https://docs.jito.wtf/",
        "https://docs.triton.one/project-yellowstone/whirligig-websockets",
    ]

    for url in urls:
        scrape_to_markdown(url)


if __name__ == "__main__":
    main()
