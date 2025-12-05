
1. Workflows page: Editing a workflow saving tags is not working.

2. ~~Executions page, Change workflow to show the workflow name. Get it by workflow ID in the executions table matching to the workflow ID in the workflows table.~~ ✓ DONE

3. 

4. 



For Later:

Credentials
Create credentials database table that caches information pulled from N8N credentials api, include tenant_id and environment_id.
Create credentials react page, similar to Workflows page, in table include link to credential in n8n. It should read from credentials table. Add page to menu.
Do not do anything regarding getting the data yet.


Node Types
Create node_types database table that caches information pulled from N8N nodetypes api, include tenant_id and environment_id.
Create Node Types react page, similar to Workflows page, in table include link to node type in n8n. It should read from nodetypes table.
Do not do anything regarding getting the data yet.


Environments page - Sync button: add Sync button for each environment. When clicked, it will alert n8n Sync in progress and run as a backend process. When done, it will alert user it's done. It will then query n8n and populate workflows, executions, credentials tables from n8n API. Sync the rows with N8N for that tenant and environment. Delete rows that don't exist in N8N. Add ones that don't exist in the table but do in N8N. And update the data in ones that exist in both.



On the workflows page, put a link for each workflow It goes to a page called workflow that passes in the workflow ID.
On the workflow page, provide details. This is generated upon view and saved to the database:
* Workflow Description - Human Readable description
* Nodes used
* Credentials used
* Security Assessment
* Dependency Checker - all external dependencies - subworkflows, APIs, etc.

Diff
* Human readable
* graph
* Semantic Parameter Diff
* Flow
* dependencies

1. Structural Diff (Node Graph Diff) — The Gold Standard
Treat workflows as graphs instead of raw JSON.
How it works
Parse workflow.nodes[] → build map keyed by id
Parse workflow.connections → adjacency list

Compare:
Node added / removed
Node type changes
Node param changes
Connection added / removed
Trigger nodes modified
Ignore ordering differences unless semantically meaningful

Why it's good
Produces “human-meaningful” diffs:
“HTTP Request node added”
“Credential reference changed”
“Connection from Node A → Node B removed”

Effort
Medium (graph parsing + structural comparison)

2. Semantic Parameter Diff
Focus on changes inside each node’s parameters object.

How it works
For each matching node ID:
Deep diff parameters
Collapse noise (e.g., automatically added fields)
Highlight important semantic fields:
URLs, credentials, queries, expressions, script code

Output example
"HTTP Request.url" changed from /v1/foo → /v1/bar
"Set.items[0].value" changed

Why it's good
Most user-visible changes are parameter changes.


Change Summaries
Generate a human-readable summary:

Example summary
Workflow: "Process Orders"

Changes:
- Added 1 node: "Check Inventory"
- Modified 2 nodes:
    • "HTTP Request": URL changed /old → /new
    • "Function Item": script changed (15 lines modified)
- Removed 1 connection: "Transform Order" → "Notify Customer"
- Trigger schedule changed: every 1 hour → every 10 minutes

Why it’s good
Great for PR comments
Great for approval workflows
Clear for non-technical stakeholders


Pipelines
* Pull requests-It can do an AI summarizer of changes and allow for user comments.
* Release
** Does it run
** Pass QA tests

* Approvals



LLM
* Cost Evaluator
* Optimizer 
* Test

Testing
* Unit Testing - For each workflow, multiple unit tests can be created. Each unit test: Inputs, expected output, actual output, Status (pass, fail)
* Custom test - python test something??





