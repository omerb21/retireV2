# Phase Closure Checklist

No phase may close unless closure package explicitly addresses these fields or Supervisor grants exception.

## Required Closure Fields

- phase name
- phase status
- relevant tests passed
- repository clean
- spec persistence verified
- drift register updated
- deferred decisions tracked
- architecture boundary impact reviewed
- contract compliance checked
- no untracked authority decisions
- commit references recorded
- supervisor closure recorded

## Field Requirements

### phase name

The closure package must identify the exact phase being closed.

### phase status

The closure package must state whether the phase is complete, blocked, deferred, or closed by exception.

### relevant tests passed

The closure package must list relevant test commands and results, or state why tests were not required.

### repository clean

The closure package must record repository status at closure time.

### spec persistence verified

The closure package must confirm that accepted authority decisions are persisted in repository specs or excepted.

### drift register updated

The closure package must confirm that known drift is resolved, tracked, or excepted.

### deferred decisions tracked

The closure package must list deferred decisions with owner phase and target phase.

### architecture boundary impact reviewed

The closure package must state whether the phase affected API, service, engine, persistence, UI, tests, or governance boundaries.

### contract compliance checked

The closure package must state whether contract usage was inspected for the affected phase flows.

### no untracked authority decisions

The closure package must confirm that no active authority decision remains only in conversation, report text, or unstored artifact.

### commit references recorded

The closure package must record relevant commit hashes for persisted artifacts and implementation changes.

### supervisor closure recorded

The closure package must record Supervisor closure approval or exception.
