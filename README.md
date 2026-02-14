# Secure Document Anonymization System

A Django-based academic paper submission and review system that performs automatic anonymization, encryption and secure evaluation workflows.

This project was developed as part of the Software Laboratory II course.

## Project Overview

The system allows authors to upload academic papers in PDF format.  
Uploaded documents are automatically anonymized using NLP-based detection and AES encryption before being assigned to reviewers.

The platform ensures:

- Double-blind review
- Secure data storage
- Role-based access control
- Automatic reviewer assignment
- PDF reconstruction after evaluation

## Technologies Used

Backend:
- Python
- Django
- SQLite

Security & NLP:
- SpaCy (Named Entity Recognition)
- Regex-based pattern detection
- AES (128-bit, ECB mode)
- PyMuPDF
- OpenCV (Face Detection & Blur)

Text Processing:
- TF-IDF keyword extraction
- Embedding-based similarity calculation

## Core Functionalities

### Automatic Text Anonymization

When a PDF is uploaded:

1. Text is extracted.
2. PERSON, EMAIL and INSTITUTION entities are detected using SpaCy and regex.
3. Each detected item is replaced with a unique tag (e.g., [ANONIM:ISIM#1]).
4. Original values are encrypted using AES.
5. Encrypted values are stored securely in the database.

### Face Blurring

- PDF pages are converted to images.
- Faces are detected using OpenCV.
- Gaussian blur is applied to face regions.
- A new anonymized PDF is generated.

### Reviewer Assignment

- TF-IDF keyword extraction is applied to document text.
- Similarity is calculated between article content and reviewer expertise.
- The best-matching reviewer is automatically selected.

### Secure De-Anonymization

After reviewer evaluation:

- Encrypted tags are decrypted.
- Original values are restored.
- Reviewer comments are appended to the PDF.
- Final document is generated for the author.

### Logging System

All major operations are recorded:

- Upload date
- Reviewer assignment
- Evaluation date
- Editor actions

Logs are stored using the `AnonimlestirmeLog` model.

## User Roles

Author:
- Upload paper
- Track submission status
- Communicate with editor
- Receive evaluation results

Reviewer:
- Access anonymized papers
- Submit evaluation
- Cannot see anonymized data

Editor:
- View all submissions
- Control anonymization
- Decrypt tags when necessary
- Monitor system logs



