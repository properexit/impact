# Geo Due Diligence AI --- Agentic AI System for Geospatial Risk Assessment

## Overview

Geo Due Diligence AI is an **agentic AI system** designed to automate
site due diligence using heterogeneous geospatial and unstructured data
sources. The system was built with a focus on **real-world applicability
in infrastructure, urban planning, and environmental risk assessment**,
aligning with use cases relevant to organizations such as Arcadis.

The platform integrates **geospatial pipelines, rule-based reasoning,
and local LLM-driven synthesis** to generate structured, explainable due
diligence reports.

------------------------------------------------------------------------

## Key Capabilities

-   **Agentic Data Orchestration**
    -   Multi-agent pipeline combining geospatial, document, and web
        intelligence
    -   Modular agents: WFS ingestion, browser agent, report agent
-   **Geospatial Intelligence**
    -   OpenStreetMap (OSM) feature extraction
    -   NRW WFS integration (ALKIS cadastral data, land use,
        infrastructure layers)
    -   Flood risk assessment via WFS
    -   Polygon-based spatial querying
-   **Hybrid Reasoning Engine**
    -   Deterministic rule-based risk scoring
    -   Signal aggregation from multiple modalities
    -   Separation of reasoning (rules) and generation (LLM)
-   **LLM-Driven Reporting**
    -   Local inference using Ollama (Mistral)
    -   Structured JSON output → converted into human-readable reports
    -   Robust fallback mechanism when LLM fails
-   **Multimodal Document Ingestion**
    -   PDF text extraction
    -   CSV structured parsing
    -   Image OCR support
-   **Explainability & Grounding**
    -   Evidence tracking across all data sources
    -   Transparent risk flags and scoring pipeline

------------------------------------------------------------------------

## System Architecture

### 1. Data Layer

-   OSM (vector features)
-   NRW WFS (cadastral + environmental layers)
-   Flood WFS
-   Web search agent (planning, zoning, environmental reports)
-   User-uploaded documents

### 2. Processing Layer

-   Spatial filtering (polygon + buffer)
-   Feature normalization → JSONL format
-   Layer aggregation and enrichment

### 3. Reasoning Layer

-   Rule-based risk engine
-   Domain-specific heuristics (zoning, contamination, protected areas)

### 4. Agent Layer

-   Browser Agent → contextual web intelligence
-   WFS Layer Builder → dynamic geospatial ingestion
-   Report Agent → LLM summarization

### 5. Presentation Layer

-   Streamlit UI
-   Interactive map (Folium)
-   Risk dashboard + evidence panel
-   PDF export

------------------------------------------------------------------------

## Why This Matters 

This project demonstrates:

-   **Applied AI Engineering**: End-to-end system integrating data
    pipelines, ML, and UI
-   **Agentic Architecture Design**: Modular agents coordinating complex
    workflows
-   **Geospatial AI Competence**: Handling real-world spatial datasets
    and WFS services
-   **Explainable AI**: Transparent risk scoring and traceable evidence
-   **Production Thinking**:
    -   Fault tolerance (LLM fallback)
    -   Separation of concerns (rules vs generation)
    -   Scalable data ingestion

------------------------------------------------------------------------

## Technology Stack

-   **Languages**: Python
-   **Geospatial**: GeoPandas, Shapely, PyOGRIO
-   **Frontend**: Streamlit, Folium
-   **AI/ML**: Ollama (Mistral), NLP pipelines
-   **Data Handling**: Pandas, JSONL pipelines
-   **Agents / Orchestration**: Custom modular agent framework

------------------------------------------------------------------------

## Setup Instructions

### 1. Environment

``` bash
python -m venv geo_env
source geo_env/bin/activate
pip install -r requirements.txt
```

### 2. Start Local LLM

``` bash
ollama serve
ollama pull mistral
```

### 3. Run Application

``` bash
streamlit run app.py
```

------------------------------------------------------------------------

## Example Workflow

1.  User draws a polygon on the map
2.  System fetches:
    -   OSM features
    -   NRW cadastral + land use layers
    -   Flood data
3.  Documents and WFS links can be uploaded
4.  Web agent enriches context (zoning, environmental plans)
5.  Risk engine computes score + flags
6.  LLM generates structured report
7.  Output:
    -   Risk dashboard
    -   Detailed report sections
    -   Evidence sources
    -   PDF export

------------------------------------------------------------------------

## Challenges Solved

-   Handling unreliable LLM outputs (robust JSON extraction + fallback)
-   Integrating heterogeneous geospatial APIs (WFS variability)
-   Designing scalable JSONL-based data pipelines
-   Maintaining explainability in multi-source AI systems

------------------------------------------------------------------------

## Future Enhancements

-   Stronger evidence-to-flag traceability
-   Improved LLM reliability (function calling / constrained decoding)
-   Layer caching and query optimization
-   Integration with enterprise GIS systems (ArcGIS / QGIS)


