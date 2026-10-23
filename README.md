# Paper Scraper

English | [中文](README.zh-CN.md)

[![Tests](https://github.com/pursurer/paper_scraper/actions/workflows/tests.yml/badge.svg)](https://github.com/pursurer/paper_scraper/actions)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A CLI and Python library that collects paper metadata from AI conferences into one CSV format.
It reads three kinds of source: the OpenReview API, conference websites, and local PDFs.

It built [top-ai-conference-papers](https://github.com/pursurer/top-ai-conference-papers):
23,197 papers from the 2025 editions of 10 conferences.

## Supported conferences

| Source | Conferences |
| --- | --- |
| OpenReview API | ICLR, ICML, NeurIPS |
| Conference websites | AAAI, IJCAI, ACL, EMNLP, NAACL, AISTATS |
| Local PDFs | AAMAS |

## Install

```bash
git clone https://github.com/pursurer/paper_scraper.git
cd paper_scraper
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Only the OpenReview source needs an account. Set it in the environment:

```bash
export OPENREVIEW_EMAIL="your_email@example.com"
export OPENREVIEW_PASSWORD="your_password"
```

or copy `config/config.example.py` to `config/config.py` and fill it in.

## Command line

```bash
# List supported conferences
python -m paper_scraper --list-conferences

# One conference, one year
python -m paper_scraper -c IJCAI -y 2024 -o ijcai_2024.csv     # website
python -m paper_scraper -c ICLR -y 2024 -o iclr_2024.csv       # OpenReview

# Several conferences and years into one folder
python -m paper_scraper -c ICLR ICML NeurIPS -y 2023 2024 --output-dir ./output

# OpenReview: keep only papers whose title, abstract or keywords fuzzily match
python -m paper_scraper -c ICLR -y 2024 -k "reinforcement learning" -o rl_papers.csv

# AAMAS: extract metadata from PDFs you have downloaded
python -m paper_scraper --pdf-dir ./aamas2025 -y 2025 -o aamas_2025.csv
```

## Python

```python
from paper_scraper import Extractor, Scraper, abstract_filter, title_filter

# OpenReview
extractor = Extractor(
    fields=["forum"],
    subfields={"content": ["title", "abstract", "keywords", "pdf"]},
)
scraper = Scraper(
    conferences=["ICLR"],
    years=["2024"],
    keywords=["reinforcement learning"],
    extractor=extractor,
    fpath="iclr_2024.csv",
)
scraper.add_filter(title_filter)
scraper.add_filter(abstract_filter)
scraper()

# Conference websites
from paper_scraper import batch_scrape, scrape_aaai, scrape_ijcai

papers = scrape_ijcai(2024, output_path="ijcai_2024.csv")
papers = scrape_aaai(2025, output_path="aaai_2025.csv")
results = batch_scrape(["IJCAI", "AAAI"], [2023, 2024], output_dir="./output")

# Local PDFs
from paper_scraper import extract_aamas_metadata

papers = extract_aamas_metadata("./aamas2025/", 2025, output_path="aamas_2025.csv")
```

## Output

Every source writes the same CSV columns:

| Column | Meaning |
| --- | --- |
| `id` | Unique id: conference, year, index |
| `title` | Paper title |
| `keywords` | Keywords |
| `abstract` | Abstract |
| `pdf` | PDF link |
| `forum` | Paper page link |
| `year` | Year |
| `presentation_type` | Oral, Spotlight or Poster |

How complete the columns are depends on the source. OpenReview fills all of them. Some
conference websites have no abstracts or keywords. For PDFs, the abstract and keywords come
from the paper itself.

## Settings

| Environment variable | Meaning | Default |
| --- | --- | --- |
| `OPENREVIEW_EMAIL` | OpenReview account email | none |
| `OPENREVIEW_PASSWORD` | OpenReview account password | none |
| `PAPER_SCRAPER_DELAY_MIN` | Shortest wait between requests, seconds | 2.0 |
| `PAPER_SCRAPER_DELAY_MAX` | Longest wait between requests, seconds | 5.0 |
| `PAPER_SCRAPER_TIMEOUT` | Request timeout, seconds | 30 |
| `PAPER_SCRAPER_RETRIES` | Retries per request | 3 |
| `PAPER_SCRAPER_OUTPUT_DIR` | Output folder | ./output |

## Tests

```bash
python -m pytest tests/
```

The 293 tests mock OpenReview and HTTP calls, so they need no account and finish in a few
seconds. CI runs them on Python 3.10, 3.11 and 3.12.

## License

MIT, see [LICENSE](LICENSE).
