# Document Paths & Mappings (PATHS.md)

When the user asks you to read or analyze files, recognize that you are running inside a Docker container. You CANNOT use Windows paths (D:\...) directly. You MUST translate them to your internal Linux paths.

Here is the exact directory mapping for files the user cares about:

| Host (Windows) Path | Container (Your) Path | Description |
| --- | --- | --- |
| `D:\Clawdbot_Docker_20260125\data\workspace` | `/home/node/clawd` | The main workspace containing scripts, Python codes, and configuration. |
| `D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume` | `/home/node/clawd/paperless_consume` | The root folder for ALL ingestible PDF/EML documents. |
| `D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\email` | `/home/node/clawd/paperless_consume/email` | The raw incoming user EML (Email) documents. |
| `D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\5Why_Analysis` | `/home/node/clawd/paperless_consume/5Why_Analysis` | The raw 5-Why analysis reports. |
| `D:\Clawdbot_Docker_20260125\data\state\Obsidian Vault` | `/home/node/clawd/obsidian_vault` | The knowledge vault where the user stores notes. |
| `D:\Clawdbot_Docker_20260125\data\state\IATF_documents` | `/home/node/clawd/iatf_documents` | Reference PDFs and specifications. |
| `D:\Clawdbot_Docker_20260125\iatf_system` | `/home/node/clawd/iatf_system_code` | The Ruby on Rails codebase for IATF. |

**Important Rule:** When the user mentions any of the folders on the left, **ALWAYS use `ls /home/node/clawd/...` or your standard file reading tools targeting the translated path on the right**. NEVER say "I cannot find the path" without checking this translation table first!
