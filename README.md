# README

**Repository:** `dpn-file-scan-service`

**Description:** `A cloud-agnostic file processing service that listens for malware scan result notifications from cloud messaging services and moves files between storage locations based on the scan outcome.`

<!-- SPDX-License-Identifier: Apache-2.0 AND OGL-UK-3.0 -->

---

## Overview

This repository contributes to the development of **secure, scalable, and interoperable data-sharing infrastructure**. It supports DSI's mission to enable **trusted, federated, and decentralised** data-sharing across organisations.

This repository is one of several open-source components that underpin DSI's **Data Preparation Node (DPN)**—a framework designed to allow organisations to manage and exchange data securely while maintaining control over their own information.

The **File Scan Service** is a file processing application developed in **Python**. It listens for malware scan result notifications from cloud messaging services and processes files based on the scan outcome, automating the secure movement of files between storage locations after malware scanning has been completed.

The service currently supports only **Microsoft Azure**, with provider hooks in place for AWS and GCP support for future release.

## Configuration and Installation

Detailed prerequisites, configuration, and installation steps for this service are maintained centrally in the [dpn-integration-playbook](https://github.com/energy-dsi/dpn-integration-playbook), so that guidance stays consistent across all DPN components and cloud providers.

### Azure Cloud Platform

- [Configuration](https://github.com/energy-dsi/dpn-integration-playbook/blob/main/Docs/03-dpn-application-deployment/azure-ado-beta/02-configuration/06-configure-dpn-file-scan-service.md)

- [Installation](https://github.com/energy-dsi/dpn-integration-playbook/blob/main/Docs/03-dpn-application-deployment/azure-ado-beta/03-installation/06-dpn-file-scan-service-installation-process.md)

Refer to the playbook for cloud-specific IAM/RBAC role requirements, environment configuration, and deployment instructions before installing this service.

## Public Funding Acknowledgment

This repository has been developed with public funding as part of the Data Sharing Infrastructure (DSI), a UK Government initiative.

## License

This repository's licensing terms, including the Apache 2.0 licence for code and the Open Government Licence v3.0 for documentation, are detailed in [LICENSE.md](./LICENSE.md).

## Security and Responsible Disclosure

We take security seriously. If you believe you have found a security vulnerability in this repository, please follow our responsible disclosure process outlined in [SECURITY.md](./SECURITY.md).

## Contributing

We welcome contributions that align with the Programme's objectives.

## Acknowledgements

This repository has benefited from collaboration with various organisations — see [ACKNOWLEDGEMENTS.md](./ACKNOWLEDGEMENTS.md).

## Support and Contact

For questions, feedback, or support requests:

- Contact the DSI team using [dsi@neso.energy](mailto:dsi@neso.energy)

## Maintained by the National Energy System Operator (NESO)

Copyright 2026 NESO. This work is licensed under the Open Government Licence 3.0 (OGL). This work has been developed by NESO using content licensed by the Department for Business and Trade (UK) under the OGL.

Licensed under the Open Government Licence v3.0.

For full licensing terms, see [OGL_LICENSE.md](./OGL_LICENSE.md).
