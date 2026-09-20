# Research job limits

The API accepts nonblank queries of at most 4,000 characters and bounded research options. Client-selected model names and unknown configuration fields are rejected; models are selected by the server settings. Branches are limited to five and depth to two. These limits reduce accidental work amplification, but still allow substantial LLM usage.

Each application process admits two running jobs and retains at most 100 jobs. Admission returns HTTP 429 while capacity is occupied. Old completed/failed jobs are evicted first; their result URLs then return 404. A failed job reports `{"status":"failed"}` and closes its event stream instead of remaining in progress forever. Detailed errors stay in server logs.

Jobs remain in memory and are lost on restart. Run a single worker: multiple workers do not share job IDs or limits. The event stream remains a single-consumer queue and does not support replay or simultaneous subscribers. Put an authenticated gateway and per-user quotas in front of a public deployment. Durable storage, distributed admission, replay and cancellation are follow-up architecture work; the current implementation does not claim to provide them.
