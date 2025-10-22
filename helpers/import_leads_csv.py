import csv
from io import StringIO

from models.lead import Lead
from typing import TypedDict
from tortoise.exceptions import IntegrityError
from datetime import datetime
from models.file import File
import pandas as pd
class ImportResults(TypedDict):
    successes: int
    errors: int
    duplicates: int
    invalid_phone_numbers: int


async def import_leads_csv(content: str, file: File) -> dict:
    results = {
        "successes": 0,
        "errors": 0,
        "duplicates": 0,
        "total": 0,
        "error_reasons": set(),
    }

    try:
        df = pd.read_csv(StringIO(content)).fillna("").astype(str)
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        required_columns = ["Name", "Email", "Phone"]
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            results["error_reasons"].add(f"Missing required columns: {', '.join(missing)}")
            results["errors"] += 1
            return results

        results["total"] = len(df)

        for idx, row in df.iterrows():
            try:
                # Check required fields
                if not row["Name"] or not row["Email"] or not row["Phone"]:
                    raise ValueError("Missing required fields: Name, Email, or Phone.")

                # Handle Add date (optional)
                add_date = None
                if "Add date" in row and row["Add date"].strip():
                    try:
                        # Normalize and parse flexible date formats
                        parsed_date = pd.to_datetime(row["Add date"], errors="raise", dayfirst=False)
                        add_date = parsed_date.date()
                    except Exception:
                        results["error_reasons"].add(f"Row {idx + 1}: Invalid date format in 'Add date'. Ignored.")

                # Create lead record
                await Lead.create(
                    name=row.get("Name", ""),
                    email=row.get("Email", ""),
                    phone=row.get("Phone", ""),
                    city=row.get("City", ""),
                    state=row.get("State", ""),
                    country=row.get("Country", ""),
                    add_date=add_date,
                    other_data=row.to_dict(),
                    file=file,
                )

                results["successes"] += 1

            except IntegrityError:
                results["duplicates"] += 1
                results["error_reasons"].add(f"Row {idx + 1}: Duplicate entry detected.")
            except ValueError as ve:
                results["errors"] += 1
                results["error_reasons"].add(f"Row {idx + 1}: {ve}")
            except Exception as e:
                results["errors"] += 1
                results["error_reasons"].add(f"Row {idx + 1}: Unexpected error — {e}")

    except Exception as e:
        results["errors"] += 1
        results["error_reasons"].add(f"Error reading the file: {e}")

    return results


def humanize_results(results: ImportResults) -> str:
    messages = []

    # Case when no rows are successfully added
    if results["successes"] == 0:
        messages.append(f"Unable to add {results['total']} row{'s' if results['total'] != 1 else ''}.")
        if results["error_reasons"]:
            messages.append("Reasons for failure:")
            messages.extend(f"- {reason}" for reason in results["error_reasons"])
        else:
            messages.append("Their is no record found.")
        return " ".join(messages)

    # Case when at least one row is successfully added
    if results["successes"] > 0:
        messages.append(f"{results['successes']} row{'s' if results['successes'] != 1 else ''} successfully added.")
        if results["errors"] > 0:
            messages.append(f"Unable to add {results['errors']} row{'s' if results['errors'] != 1 else ''}.")
        if results["duplicates"] > 0:
            messages.append(f"Out of which {results['duplicates']} had invalid or duplicate values.")
    
    return " ".join(messages)
