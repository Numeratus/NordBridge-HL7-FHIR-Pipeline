# NordBridge - HL7 v2 → FHIR R4 Integration Pipeline

> A real-world Health IT integration project built with Mirth Connect 4.5.2, demonstrating end-to-end HL7 v2 message processing, FHIR R4 transformation, and clinical data visualization.

![Mirth Connect](https://img.shields.io/badge/Mirth_Connect-4.5.2-blue)
![FHIR](https://img.shields.io/badge/FHIR-R4-green)
![HL7](https://img.shields.io/badge/HL7-v2.5-orange)
![Python](https://img.shields.io/badge/Python-3.x-yellow)

---

## Clinical Context

In most hospitals, systems don't talk to each other out of the box. A patient gets admitted in one system, their vitals are recorded in another, and their discharge is documented in a third. The result is fragmented data, manual re-entry, and avoidable errors.

**NordBridge** simulates the integration layer that bridges these gaps, the kind of middleware that sits between a hospital's ADT system and its FHIR-based platforms, transforming legacy HL7 v2 messages into modern FHIR R4 resources in real time.

The fictional hospital **Nordpeak Medical Center** is used throughout as the data source.

---

## Architecture

```
┌─────────────────────────────────────┐
│         Nordpeak Medical Center     │
│   (Fictional Hospital HIS/ADT)      │
└────────────────┬────────────────────┘
                 │ HL7 v2 over MLLP/TCP
                 ▼
┌─────────────────────────────────────┐
│         Mirth Connect 4.5.2         │
│                                     │
│  Channel 1: ADT^A01 (Admission)     │
│  Channel 2: ORU^R01 (Vital Signs)   │
│  Channel 3: ADT^A03 (Discharge)     │
│                                     │
│  Per channel:                       │
│  - MLLP TCP Listener                │
│  - HL7 v2 Parser                    │
│  - JavaScript Transformer           │
│  - FHIR R4 Resource Builder         │
│  - HTTP Sender (POST to FHIR)       │
└────────────────┬────────────────────┘
                 │ FHIR R4 JSON over HTTPS
                 ▼
┌─────────────────────────────────────┐
│       HAPI FHIR Server (Public)     │
│       https://hapi.fhir.org/baseR4  │
│                                     │
│  Resources created:                 │
│  - Patient                          │
│  - Encounter                        │
│  - Observation (Vitals)             │
└────────────────┬────────────────────┘
                 │ REST API
                 ▼
┌─────────────────────────────────────┐
│     Python / Streamlit Dashboard    │
│     nordbridge_dashboard.py         │
│                                     │
│  - Patient demographics             │
│  - Encounter status                 │
│  - Vital signs display              │
└─────────────────────────────────────┘
```

---

## Channels

### Channel 1 - ADT^A01 (Patient Admission)
**Port:** 6661 | **Protocol:** MLLP | **Output:** FHIR Patient + Encounter

Triggered when a patient is admitted. The channel:
1. Receives the HL7 ADT^A01 message over MLLP
2. Extracts patient demographics from the PID segment (name, DOB, gender, address, phone)
3. Extracts visit data from the PV1 segment (ward, room, bed, attending physician, admit time)
4. Maps HL7 gender codes (M/F/O) to FHIR gender values
5. Converts HL7 date format (YYYYMMDDHHMMSS) to FHIR ISO 8601
6. POSTs a FHIR R4 Patient resource to HAPI FHIR
7. Captures the server-assigned Patient ID from the response
8. POSTs a FHIR R4 Encounter resource linked to that Patient

### Channel 2 - ORU^R01 (Vital Signs)
**Port:** 6662 | **Protocol:** MLLP | **Output:** FHIR Observation

Triggered when vital signs are recorded. The channel:
1. Receives the HL7 ORU^R01 message over MLLP
2. Extracts observations from the OBX segments (heart rate, temperature, etc.)
3. Maps each observation to a LOINC code (the international standard for clinical measurements)
4. POSTs a FHIR R4 Observation resource linked to the correct Patient via MRN

### Channel 3 - ADT^A03 (Patient Discharge)
**Port:** 6663 | **Protocol:** MLLP | **Output:** FHIR Encounter (updated)

Triggered when a patient is discharged. The channel:
1. Receives the HL7 ADT^A03 message over MLLP
2. Looks up the existing Encounter on the FHIR server by the encounter identifier
3. Updates the Encounter status to `finished`
4. Adds the discharge timestamp to the Encounter period

---

## Project Structure

```
nordbridge/
│
├── channels/
│   ├── Admission.xml        # Mirth channel export - ADT^A01
│   ├── Vitals.xml           # Mirth channel export - ORU^R01
│   └── Discharge.xml        # Mirth channel export - ADT^A03
│
├── test_messages/
│   ├── nordbridge_test_adt_a01.hl7   # Admission test message
│   ├── nordbridge_test_oru_r01.hl7   # Vital signs test message
│   └── nordbridge_test_adt_a03.hl7   # Discharge test message
│
├── dashboard/
│   └── nordbridge_dashboard.py       # Streamlit patient chart
│
└── README.md
```

---

## Getting Started

### Prerequisites
- [Mirth Connect 4.5.2](https://www.nextgen.com/solutions/interoperability/mirth-solutions/mirth-connect) installed and running
- Python 3.x
- `streamlit` and `requests` Python libraries

### 1. Import Channels into Mirth Connect

In the Mirth Connect Administrator:
1. Go to **Channels** → **Import Channel**
2. Import `channels/Admission.xml`
3. Import `channels/Vitals.xml`
4. Import `channels/Discharge.xml`
5. Deploy all three channels

### 2. Send Test Messages

Use the following Python one-liner to send a test message over MLLP (no extra libraries needed):

```bash
python3 -c "
import socket, time
START_BLOCK = b'\x0b'
END_BLOCK   = b'\x1c\x0d'
msg = open('test_messages/nordbridge_test_adt_a01.hl7', 'rb').read().replace(b'\n', b'\r')
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('localhost', 6661))
    s.sendall(START_BLOCK + msg + END_BLOCK)
    time.sleep(1)
    print('ACK:', s.recv(4096))
"
```

Repeat for the other messages by changing the filename and port (6662 for vitals, 6663 for discharge).

A successful response contains `MSA|AA` - **Application Accept**.

### 3. Verify on HAPI FHIR

Check created resources directly on the public FHIR server:

```
# Patient
https://hapi.fhir.org/baseR4/Patient?identifier=http://nordpeak.de/fhir/patients|NP-2026-004

# Encounter
https://hapi.fhir.org/baseR4/Encounter?identifier=http://nordpeak.de/fhir/encounters|NP-2026-004-ENC

# Observations
https://hapi.fhir.org/baseR4/Observation?_tag=nordbridge&_count=100
```

### 4. Run the Dashboard

```bash
pip install streamlit requests
streamlit run dashboard/nordbridge_dashboard.py
```

Opens at `http://localhost:8501` - shows patient demographics, encounter status, and vital signs pulled live from the FHIR server.

---

## HL7 & FHIR Concepts Demonstrated

| Concept | Where Used |
|---|---|
| MLLP framing | All channels - wraps HL7 messages for TCP transport |
| HL7 v2 ADT segments | PID (patient), PV1 (visit), EVN (event) |
| HL7 v2 ORU segments | OBX (observation), OBR (observation request) |
| FHIR R4 Patient | Channel 1 destination |
| FHIR R4 Encounter | Channel 1 destination + Channel 3 update |
| FHIR R4 Observation | Channel 2 destination |
| LOINC codes | Vital signs coding in Observation resources |
| SNOMED CT | Encounter type coding |
| HL7 ACK/NACK | Mirth auto-generates AA acknowledgments |
| Conditional mapping | HL7 patient class → FHIR encounter class (IMP/EMER/AMB) |
| Response transformer | Extracting FHIR server ID to chain Patient → Encounter |

---

## Tech Stack

- **Mirth Connect 4.5.2** - Integration engine
- **HL7 v2.5** - Source message format
- **FHIR R4** - Target resource format
- **HAPI FHIR** - Public FHIR server (test environment)
- **JavaScript** - Mirth transformers
- **Python 3** - MLLP sender + Streamlit dashboard
- **Streamlit** - Dashboard UI

---

## References

- [HL7 v2.5 Specification](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=144)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [LOINC - Vital Signs Panel](https://loinc.org/85353-1/)
- [IHE Integration Profiles](https://www.ihe.net/resources/profiles/)
- [Mirth Connect Documentation](https://docs.nextgen.com/en-US)
