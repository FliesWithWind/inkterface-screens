# Security

## Reporting

Found a problem with a screen in this catalog, the signing setup, or the tools? Open a private
security advisory on this repository, or contact the owner (@FliesWithWind). Please do not file a
public issue for a security problem.

## How this catalog is trusted

- The published `index.json` is signed with an Ed25519 key. The plugin ships the matching public key
  and verifies the signature before it trusts the index. An unsigned or wrongly signed index is
  rejected; CI refuses to publish an unsigned index.
- Each screen package's `sha256` and size are recorded in the index, so the plugin can check what it
  downloaded matches what was signed.

## Code screens

A code screen (`screen.py`) runs on the user's machine as their own account. The plugin runs it in a
guarded child process (empty environment, wall-clock timeout, memory/CPU/file-size limits) -- a
**guardrail against buggy screens, not a sandbox**. An approved `screen.py` can still read the user's
files and use the network.

The real protection is approval: the plugin shows the user the `sha256` of `screen.py` and the code
does not run until they approve exactly that hash. Editing the code revokes the approval. In this
repo, every `screen.py` change is reviewed line by line by the owner (enforced by CODEOWNERS).
