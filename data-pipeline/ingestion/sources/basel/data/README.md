# Basel Convention Party Data

Place a downloaded Basel party status file here as `basel_parties.csv` or `basel_parties.xlsx`.

## How to obtain the data

1. Visit: https://www.basel.int/Countries/StatusofRatifications/PartiesSignatories/tabid/4499/Default.aspx
2. Download the party list (Excel or CSV)
3. Save as `basel_parties.csv` in this directory

## Expected columns

| Column | Description |
|--------|-------------|
| `ISO3` | ISO 3166-1 alpha-3 country code |
| `Country` | Country name |
| `Is_Party` | `Yes`/`No` — whether country has ratified the Basel Convention |
| `Ban_Amendment` | `Yes`/`No` — whether the Basel Ban Amendment is ratified |
| `Ratification_Year` | Year of Basel Convention ratification |
| `Ban_Ratification_Year` | Year of Ban Amendment ratification (if applicable) |

The parser accepts multiple column name spellings — see `parse.py` for the full alias map.

## Setting an alternative path

Set the `BASEL_LOCAL_PATH` environment variable to point to any CSV/Excel file
at a different location.
