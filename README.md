# SnapChef 

Dette er en Streamlit-applikasjon guaid for hva som må til for å starte nettsiden 

---

## Slik starter du appen

Følg instruksjonene under for ditt operativsystem for å installere avhengigheter og kjøre applikasjonen.

### 1. Åpne terminalen
Åpne prosjektmappen i terminalen din (f.eks. integrert terminal i VS Code).

---

### 2. Opprett og aktiver et virtuelt miljø (Valgfritt, men anbefalt)

#### Windows (PowerShell / Command Prompt)
```bash
python -m venv venv
.\venv\Scripts\activate
```
*(Dersom `python` ikke fungerer, prøv `py -m venv venv`)*

#### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Installer nødvendige pakker

Når det virtuelle miljøet er aktivert, installer alle avhengighetene fra `requirements.txt`:

```bash
pip install -r requirements.txt
```

> **Merk om første kjøring:**  
> Første gang appen kjøres vil bibliotekene `easyocr` og `rembg` automatisk laste ned sine moduler.
---

### 4. Start Streamlit-appen

Kjør følgende kommando for å starte applikasjonen:

#### Windows
```bash
streamlit run app.py
```
*(Eller: `py -m streamlit run app.py`)*

#### macOS /Linux
```bash
streamlit run app.py
```
*(Eller: `python3 -m streamlit run app.py`)*

---

Nettleseren din vil automatisk åpne appen på `http://localhost:8501`. Om den ikke åpnes automatisk, kan du klikke på lenken som dukker opp i terminalen.
