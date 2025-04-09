Okay, this is excellent detail. Let's integrate these specific data points and exclusion criteria into the PRD, focusing on delivering CLI support for SATA, SAS, and NVMe with this specific grading logic in Phase 1 (MVP).

Here are the updated sections of the PRD:

---

*(Sections unchanged from the previous version are omitted for brevity)*

## PRD Overview and Document Control

### Document Information

-   **Product/Feature Name:** CDI (Component Drive Intelligence) Grading Tool v1.0
-   **Document Owner:** Jonmichael Hands, Product Manager (Acting)
-   **Date Created:** 2025-04-08
-   **Last Updated:** **2025-04-09** *(Updated)*

### Version History

| Version | Date       | Author           | Description of Changes                                                                |
| :------ | :--------- | :--------------- | :------------------------------------------------------------------------------------ |
| 1.0     | 2025-04-08 | Jonmichael Hands | Initial comprehensive draft based on input                                            |
| **1.1** | **2025-04-09** | **Jonmichael Hands** | **Revised Phase 1 scope for SATA/SAS/NVMe CLI, added specific data points & grading logic.** |

## Executive Summary

*(Problem Statement, Business Objectives remain largely the same but the value proposition is strengthened by broader protocol support)*

### Proposed Solution

The CDI Grading Tool is a **Command-Line Interface (CLI)** software application designed to automate and standardize the health assessment of multiple storage devices (**SATA, SAS, and NVMe**) simultaneously. It interfaces with connected drives to extract key health indicators including standardized attributes (SMART, NVMe Log Pages), vendor-specific log pages, device telemetry, and self-test results. Using a defined set of **pass/fail/flag criteria based on industry knowledge and specific thresholds (detailed below)**, the tool assigns a clear status to each drive. It generates concise reports summarizing drive vital data and highlighting drives that fail criteria or warrant caution, enabling rapid disposition decisions within ITAD and data center workflows.

## Strategic Context

### Project Scope

**In Scope (v1.0 - MVP):**

* Core grading engine applying defined Pass/Fail/Flag rules based on extracted drive data.
* **Command-Line Interface (CLI)** for primary interaction and automation.
* Support for **SATA, SAS, and NVMe** HDDs and SSDs connected via standard OS interfaces (direct connect, HBAs, recognized adapters).
* Detection and identification of connected drives (Vendor, Model, SN, Firmware, Capacity, Protocol).
* Extraction of specified "Necessary Properties" (see Functional Requirements) across protocols.
* Basic status output (e.g., Pass, Fail, Flagged - Heavy Use).
* Generation of a summary report (CSV format) listing all drives, with clear identification of Fail/Flagged drives and core statistics (SN, Status, Failure Reason, POH, Reallocated/PctUsed etc.).
* Support for Windows and major Linux distributions.
* Utilize underlying open-source tools like `smartmontools`, `nvme-cli`, `sg_utils` where applicable and licensed appropriately.

**Out of Scope (v1.0 - MVP):**

* Graphical User Interface (GUI).
* *Running* new drive self-tests or vendor diagnostics (focus is on reading *historical* results).
* Deep forensic analysis or data recovery features.
* Data wiping/sanitization capabilities.
* Direct integration with specific ITAD ERP systems (Future consideration).
* Checking against a database of *drive-specific* specifications (e.g., temperature limits, load cycle limits) - v1 uses generic or configurable fixed thresholds.
* Cloud-based reporting or analytics platform.
* Mobile application.
* Predictive failure analysis beyond defined threshold rules.
* Real-time monitoring.
* **Physical/Visual damage assessment** (This remains a manual ITAD process step).

## User-Centered Requirements

*(Personas, Scenarios remain largely the same, but apply across SATA/SAS/NVMe)*

### User Stories

*(Adding/Modifying stories based on new scope)*

* **(M) As Tony (ITAD Tech), I want to initiate a scan of all connected SATA, SAS, and NVMe drives with a single command, so that I can process mixed batches efficiently.**
* **(M) As Tony, I want the tool to automatically identify the Serial Number, Model, Firmware, Capacity, and Interface Protocol for each drive.**
* **(M) As Tony, I want to receive a clear status (Pass/Fail/Flagged) for each drive based on the defined "Exclusion Properties", so that I can make immediate sorting decisions.**
* **(M) As Sarah (DC Manager), I want the grading to be based on objective data points like reallocated sectors (HDD), percentage used (SSD), available spare (SSD), media errors (NVMe), and self-test history, so that the assessment is consistent and data-driven.**
* **(M) As Mike (Resale Lead), I want a CSV report summarizing all processed drives, highlighting the 'Fail'/'Flagged' ones with the specific reason (e.g., 'Reallocated>10', 'AvailSpare<=97%'), human-readable Power-On Hours, and key wear indicators (Reallocated/PctUsed), so I can quickly triage inventory and justify pricing.**
* **(S) As Tony, I want Power-On Hours displayed in a human-readable format (years/days/hours) in the report, so I can easily understand drive age/usage.**
* **(S) As Mike, I want HDDs with a calculated workload exceeding 550TB/year to be flagged as 'Heavy Use' in the report, so I can consider this during pricing or grading refinement.**
* **(M) As a Developer, I need the tool to query specific NVMe log pages (02h - SMART, Error Log, potentially Telemetry/OCP) to gather necessary SSD health data.**
* **(M) As a Developer, I need the tool to query relevant ATA SMART attributes and Log Pages / SCSI Log Pages for SATA/SAS drives.**
* **(C) As Sarah, I want the report to include host read/write data (in GB/TB) and temperature information (Avg/Max or NVMe times) for informational purposes.**

*(User Journeys remain similar but now handle mixed-protocol batches)*

## Functional Requirements

### Core Features

1.  **Drive Detection & Identification (M):**
    * Scan system for connected storage devices (SATA, SAS, NVMe) visible to the OS.
    * Extract and report: Vendor, Model Number, Serial Number, Firmware Version, Capacity, Interface Protocol (SATA/SAS/NVMe).
    * Handle errors in identification gracefully.
2.  **Drive Data Extraction (M):**
    * **All Protocols:** Query Power-On Hours (POH). Query drive self-test log history. Query Host Bytes Written, Host Bytes Read.
    * **SATA/SAS HDD:** Query standard SMART attributes. Query specific log pages for Head Load/Unload Count, Spindle Start/Stop Count, Average/Maximum Temperature. Query Reallocated Logical Sector Count, Current Pending Sector Count.
    * **SATA/SAS SSD:** Query standard SMART attributes. Query specific log pages for Average/Maximum Temperature. Query Percentage Used/Endurance Used, Available Spare Percentage (if available via SMART/logs).
    * **NVMe SSD:** Query Log Page 02h (SMART / Health Information - includes Critical Warning flags, Temperature, Available Spare, Percentage Used, Media and Data Integrity Errors, POH, Power Cycles, Host Reads/Writes). Query Log Page 01h (Error Information Log Entries). Query Log Page 06h (Device Self-test Log). *Potential (C):* Query Telemetry Host-Initiated Log (Log ID 07h), Telemetry Controller-Initiated Log (Log ID 08h). Query OCP Cloud SSD Log Page C0h (if supported and identifiable). Extract Warning Composite Temperature Time, Critical Composite Temperature Time from Log Page 02h.
    * Reliably parse required data from different protocol outputs. Handle missing/unsupported attributes/logs.
3.  **Status Engine (Based on Exclusion Properties) (M):**
    * Apply rules based on extracted data to assign a status: `Pass`, `Fail`, `Flagged`, `Error`.
    * **Failure Conditions (Result in `Fail` Status):**
        * Any failed drive self-test reported in the drive's log history (across all protocols).
        * *(Manual Check - Out of Scope)* Failed vendor diagnostic test (If results can be programmatically determined from logs, include; otherwise, remains manual).
        * **HDD:** Current Pending Sector Count > 10.
        * **HDD:** Reallocated Sector Count > 10.
        * **SSD (All):** Percentage Used > 100%.
        * **SSD (All):** Available Spare <= 97%.
        * **NVMe SSD:** Drive Media and Data Integrity Errors > `TBD (e.g., 10)` *(Requires research/SME input)*.
        * **NVMe SSD:** Critical Composite Temperature Time > `TBD (e.g., 0)` minutes *(Requires research/SME input)*.
    * **Flag Conditions (Result in `Flagged` Status):**
        * **HDD:** Calculated workload > 550 TB/year (Workload = Total Host Read/Write Bytes / POH in years). Assign Flag: `Heavy Use`.
        * **NVMe SSD:** Warning Composite Temperature Time > `TBD (e.g., 60)` minutes *(Requires research/SME input)*. Assign Flag: `Temp Warning History`.
    * *(Out of Scope for V1 Check, Data Collection Only):* HDD Start/Stop count, Load/Unload count, Max Temperature exceeding drive spec. Tool will collect these values for reporting.
    * Drives not meeting any Fail/Flag criteria receive `Pass` status.
    * Drives where essential data cannot be read receive `Error` status (with reason).
4.  **Reporting (M):**
    * Output summary to console, highlighting Fail/Flagged drives.
    * Generate a summary report in CSV format.
    * **CSV Columns (Minimum):** `SerialNumber`, `Model`, `Firmware`, `Capacity(GB)`, `Protocol`, `Status`, `FailureReason/Flag`, `POH_Readable`, `POH_Hours`, `ReallocatedSectors (HDD)`, `PendingSectors (HDD)`, `PercentUsed (SSD)`, `AvailableSpare% (SSD)`, `MediaErrors (NVMe)`, `HostReads(GB)`, `HostWrites(GB)`, `MaxTemp`, `AvgTemp` / `WarningTempTime(min)`, `CriticalTempTime(min)`.
    * Format POH into a human-readable string (e.g., "2y 15d 8h").
    * Format Bytes Read/Written into GB or TB.
5.  **CLI Interface (M):** *(As previously defined)*

#### Feature Example: Status Engine (M)

-   **Description:** Analyzes extracted drive data against the defined "Exclusion Properties" to assign a status (Pass, Fail, Flagged, Error).
-   **Acceptance Criteria:**
    * SATA HDD with Reallocated Sectors = 15 is assigned `Fail` status with reason `Reallocated>10`.
    * NVMe SSD with Available Spare = 96% is assigned `Fail` status with reason `AvailSpare<=97%`.
    * SATA SSD with Percentage Used = 90% and Available Spare = 100% and no failed self-tests is assigned `Pass` status.
    * SAS HDD with POH = 18000 hours and Host Writes = 400TB, Host Reads = 300TB (~350TB/year) is flagged `Heavy Use` but may still be `Pass` if no other fail criteria met (Status: `Pass`, Flag: `Heavy Use`). *(Revised logic: Flag separate from Pass/Fail status)*
    * A drive whose self-test log shows a prior failure entry is assigned `Fail` status with reason `FailedSelfTestHistory`.
    * A drive where SMART/NVMe Logs cannot be read results in `Error` status with reason `DataReadError`.
-   **Happy Flow:** Tool reads data -> Compares values against exclusion rules -> No rules triggered -> Assigns `Pass`. A non-fatal rule triggered (e.g., Heavy Use) -> Assigns `Pass` + corresponding Flag. A fatal rule triggered -> Assigns `Fail` + reason.
-   **Unhappy Flow:** Essential data read fails -> Tool logs error -> Assigns `Error` + reason. Non-essential data read fails -> Tool logs warning, continues grading, reports missing data.
-   **Design References:** N/A for CLI.

### Non-Functional Requirements

*(Performance, Reliability, Usability, Security, Maintainability as before. Compatibility updated)*
* **Compatibility:**
    * OS: Windows 10/11 (64-bit), Ubuntu Linux LTS (e.g., 22.04, 24.04), RHEL/CentOS compatible.
    * Interfaces (MVP): SATA, SAS, NVMe drives recognized by the OS disk subsystem and accessible via standard tools (`smartmontools`, `nvme-cli`, `sg_utils`). Requires appropriate controllers/HBAs/adapters.
    * Dependencies: Relies on OS ability to see the drives. Requires `smartmontools`, `nvme-cli` (for NVMe), `sg_utils` (potentially for SAS) to be installed or bundled/called by the tool. Requires necessary permissions (admin/root).

## Technical Specifications

### System Architecture

*(As before, likely Python/Go/Rust CLI calling external tools)*
* Invokes external utilities like `smartmontools` (SATA/SAS/USB), `nvme-cli` (NVMe), potentially `sg_utils` (SAS specific commands if needed beyond smartmontools).

### Technical Dependencies

* **Core:** `smartmontools` (v7.x+ recommended for broad support).
* **NVMe:** `nvme-cli` (v1.9+ recommended).
* **SAS:** `sg_utils` (if specific SCSI commands beyond smartmontools are needed).
* **OS:** Standard OS libraries/APIs for device enumeration.
* **Language Runtimes:** (As applicable).

*(Data Requirements, Technical Constraints updated slightly)*
### Technical Constraints

* Reliant on OS correctly identifying drives and necessary kernel modules/drivers being loaded (esp. for NVMe, SAS HBAs).
* Reliant on the capabilities and correctness of the underlying tools (`smartmontools`, `nvme-cli`, `sg_utils`) for specific drive models and firmware versions.
* Performance scaling with SAS/NVMe might differ from SATA due to protocol/driver overhead.
* Accessing SAS/NVMe devices often requires specific group memberships or root privileges on Linux.
* Parsing numerous vendor-specific SMART attributes or log pages requires ongoing maintenance.
* License compliance for all bundled/called utilities is critical.

## Implementation Plan

### Development Phases

1.  **Phase 0: Research & Setup (2-4 Weeks)** *(Slightly extended for multi-protocol research)*
    * Finalize specific commands/attributes/logs for SATA, SAS, NVMe necessary properties & exclusion checks.
    * Confirm usage strategy & license compliance for `smartmontools`, `nvme-cli`, `sg_utils`.
    * Establish dev environment, CI/CD. Define config file structure (if needed beyond CLI args) & detailed report format.
2.  **Phase 1: Core CLI & Multi-Protocol Grading (MVP) (8-12 Weeks)** *(Extended due to added protocols)*
    * Implement drive detection for SATA, SAS, NVMe (Win/Linux).
    * Integrate data extraction using chosen libraries/tools across all 3 protocols.
    * Build Status Engine based on defined Exclusion Properties.
    * Implement CLI command structure. Implement CSV reporting with all specified columns.
    * Unit tests and integration testing across protocols. Alpha release.
3.  **Phase 2: Refinements & Beta (4-6 Weeks)** *(Was Phase 2+3)*
    * Refine reporting formats (human readability, error details).
    * Address Alpha feedback, improve error handling.
    * Broader testing with diverse hardware (SATA/SAS/NVMe drives, controllers, adapters). Beta release to pilot partners.
4.  **Phase 3: Hardening & Release (2-4 Weeks)** *(Was Phase 3 hardening)*
    * Address Beta feedback. Finalize documentation. Performance tuning. Prepare release builds. v1.0 Release.

*(Timeline & Resources section should now reflect the increased complexity of Phase 1)*
### Timeline and Milestones

*(Adjust target dates based on revised phase estimates)*

| Milestone                 | Target Start Date | Target End Date   | Key Deliverables                                                              |
| :------------------------ | :---------------- | :---------------- | :---------------------------------------------------------------------------- |
| Phase 0: Research/Setup   | 2025-04-15        | **2025-05-13** | Tech stack/libs confirmed, Commands spec'd, Config/Report spec, CI/CD setup |
| Phase 1: MVP Dev          | 2025-05-14        | **2025-08-02** | Working CLI (SATA/SAS/NVMe), Status Engine, CSV report, Alpha Build         |
| Phase 2: Refinements/Beta | 2025-08-05        | **2025-09-13** | Enhanced reporting, Error handling++, Beta Build                              |
| Pilot Partner Beta Test   | 2025-09-16        | 2025-10-11        | User feedback, Bug reports, Performance data                                  |
| Phase 3: Hardening/Release | 2025-10-14        | **2025-10-25** | Release Candidate, Final Docs, v1.0 Release Package                             |
| **v1.0 Launch** | **2025-10-28** |                   | Publicly available v1.0                                                       |

*(Note: Increased Phase 1 duration impacts subsequent dates. Resource needs might increase slightly, potentially needing developer expertise across different storage protocols.)*

### Risk Assessment

*(Add/modify risks related to multi-protocol support)*

| Risk                                                  | Likelihood (L/M/H) | Impact (L/M/H) | Mitigation Strategy                                                                                                   |
| :---------------------------------------------------- | :----------------- | :------------- | :-------------------------------------------------------------------------------------------------------------------- |
| **Complexity of SAS/NVMe Interaction** | **M** | **H** | Leverage established tools (`nvme-cli`, `sg_utils`), allow sufficient time for testing, require specific developer expertise. |
| Inaccurate/Inconsistent Grading Logic                 | M                  | H              | Validate rules with SME, test against known states, use pilot feedback, clearly define TBD thresholds.                  |
| **Variability in Log/Attribute Support Across Vendors** | **H** | **M** | Design for graceful handling of missing data, focus on widely supported key metrics, document known gaps.               |
| Poor Performance with High Drive Counts               | M                  | M              | Design for concurrency, benchmark early (esp. with mixed protocols), optimize critical paths.                         |
| Compatibility Issues (OS, Adapters, Drives, Firmware) | H                  | M              | Rely on robust libs, test on target platforms/hardware, document known issues, clear error messages.                |
| Dependency Licensing Issues (GPL etc.)                | L                  | H              | Legal review early, choose libraries/invocation methods carefully, design architecture for compliance.                |
| Scope Creep                                           | M                  | M              | Strict adherence to defined v1.0 scope, clear communication, backlog grooming.                                        |
| Underlying Tool Limitations/Bugs                    | M                  | M              | Stay updated on releases, contribute fixes upstream if possible, build workarounds, test specific versions.           |

*(Testing Strategy needs expansion)*
## Testing Strategy

### Test Scenarios

*(Add SAS/NVMe specifics)*
* **Core Functionality:**
    * Scan and correctly identify various **SATA, SAS, and NVMe** HDD/SSD models from major vendors.
    * Accurately extract specified "Necessary Properties" for each protocol.
    * Apply Pass/Fail/Flag grading rules correctly based on mock data and real drives (covering all exclusion properties).
    * Generate CSV report in the correct format with accurate data, including human-readable POH.
* **Protocol Specific:**
    * Test with various SAS HBAs and NVMe controllers/motherboards.
    * Verify correct invocation of `smartmontools`, `nvme-cli`, `sg_utils`.
    * Test specific NVMe log page parsing (01h, 02h, 06h, C0h if possible).
    * Test specific SAS log page/mode page parsing if used beyond smartmontools.
* **Concurrency & Mixed Mode:**
    * Run scans on multiple drives simultaneously, including mixtures of SATA, SAS, and NVMe. Monitor performance and stability.
* **Edge Cases:** *(As before, but apply across protocols)* Test failing drives, new drives, drives with limited reporting, unsupported drives, connection/disconnection, corrupted config (if used).
* **Compatibility:** *(As before)* Test Win/Linux, various adapters/controllers.
* **CLI Usability:** *(As before)*

*(Acceptance Criteria & Quality Gates remain similar but implicitly cover the expanded scope)*

## Appendix

### Open Issues and Questions

* **Final TBD thresholds for NVMe:** Warning Composite Temperature Time, Critical Composite Temperature Time, Media and Data Integrity Errors. (Requires research/SME consensus).
* Confirm specific `sg_utils` commands needed for SAS if `smartmontools` coverage is insufficient for required data.
* Strategy for handling drives that *don't* report specific required metrics (e.g., Available Spare on older SSDs)? Fail? Pass with warning? Configurable? (Recommendation: Report missing data, potentially `Error` if critical for grading).
* Source for drive specifications if checks beyond fixed thresholds are desired in future versions.
* Confirm licensing strategy for the CDI tool itself (Proprietary, Open Source?). Review licenses of *all* dependencies (`smartmontools`, `nvme-cli`, `sg_utils`).
* Detailed error code list for reporting specific failure reasons (e.g., `ERR_READ_SMART`, `ERR_READ_NVME_LOG`, `FAIL_REALLOC`, `FAIL_SPARE`).

*(References and Glossary updated implicitly)*
### Glossary
*(Additions)*
* **SAS:** Serial Attached SCSI - Common enterprise storage interface.
* **NVMe:** Non-Volatile Memory Express - High-speed interface for SSDs.
* **HBA:** Host Bus Adapter - Connects a host system to storage devices (often used for SAS/SATA).
* **sg_utils:** Linux utility package for sending SCSI commands.
* **nvme-cli:** Linux utility package for NVMe drive management.
* **Log Page (NVMe/SCSI):** Standardized structures containing drive diagnostic and status information.

---

This revised PRD now reflects the expanded Phase 1 scope to include SATA, SAS, and NVMe CLI support, incorporating the detailed data points and specific exclusion logic provided. The timeline and risks have been adjusted to account for the increased complexity. Remember to resolve the "TBD" items and open questions during the research/setup phase.