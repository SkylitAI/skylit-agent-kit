# Security

Do not publish credentials, private data or exploitable security details in an issue. Report concerns privately to Skylit support through the [official site](https://www.skylit.ai/), including a minimal sanitized reproduction.

Use your own account and least-privilege access. Revoke or rotate exposed keys. Keep TLS verification, host sandboxing and tool approvals enabled. Treat retrieved documents and tool outputs as untrusted data, never as instructions that authorize new actions.

The sample is offline and synthetic. The account example has one fixed HTTPS destination, rejects redirects, bounds response size and does not retry. It does not implement paid market-data workflows. Direct MCP clients use the host and service controls; this kit's prompt guidance cannot enforce their budgets.

Pull-request checks must not receive production credentials or execute untrusted code in a privileged workflow. Do not add `pull_request_target` execution of contribution code. Review dependency changes and action pins. Generated reports stay local and are ignored by Git.
