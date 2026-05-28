import argparse
import json
import os
import sys
from pathlib import Path

# Add src to sys.path to allow importing scrapers.
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

try:
    from timetable_scrapers import ScraperRegistry
except ImportError as e:
    print(f"Could not import scrapers. {e}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Extract University Exam Schedules using a scraper."
    )

    parser.add_argument(
        "scraper_name",
        help=f"Name of the scraper to use {ScraperRegistry.list_scrapers()}",
    )

    parser.add_argument("input_file", help="Path to the Excel file")

    parser.add_argument(
        "output_file",
        help="Path to where you want your JSON file to be located and its name",
    )

    args = parser.parse_args()

    scraper_name = args.scraper_name
    input_file = args.input_file
    output_file = args.output_file

    # Ensure the output der exists
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Ensure input file exists
    if not os.path.exists(input_file):
        print(f"Error: {input_file} does not  exist")
        sys.exit(1)

    # Load relevant Scraper
    try:
        scraper = ScraperRegistry.get_scraper(scraper_name)
    except ValueError as e:
        print(f"{e}")

        available = ScraperRegistry.list_scrapers()
        print(f"Available Scrapers: {available}")

        sys.exit(1)

    try:
        with open(input_file, "rb") as f:
            entries = scraper.extract(f)
    except Exception as e:
        print(f"Error during extraction: {e}")
        sys.exit(1)

    print(f"Extracted {len(entries)}")

    try:
        from timetable_scrapers.professor_contract import build_ingest_payload
        payloads = build_ingest_payload(scraper_name, entries, chunk_size=1000000)
        
        all_items = []
        for p in payloads:
            all_items.extend(p["items"])
            
        final_output = {"items": all_items}
    except Exception as e:
        print(f"Error building payload: {e}")
        sys.exit(1)

    print(f"Saving to: {output_file}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)

    print("Success")


if __name__ == "__main__":
    main()
