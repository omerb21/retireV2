# Runtime Evidence Commands

These commands are Windows PowerShell compatible and are intended for V2 runtime evidence collection. Run from the repository root unless a command explicitly changes location.

## Repository Status And Commit

```powershell
git status --short --untracked-files=all
git rev-parse HEAD
git log --oneline -3
```

## Backend Route Listing

```powershell
Set-Location backend
python -c "from app.main import app; [print(','.join(sorted(getattr(route, 'methods', []) or [])) + ' ' + getattr(route, 'path', '') + ' ' + getattr(route, 'name', type(route).__name__)) for route in app.routes]"
Set-Location ..
```

## Backend Test Collection

```powershell
Set-Location backend
python -m pytest --collect-only -q
Set-Location ..
```

## Backend Test Execution

```powershell
Set-Location backend
python -m pytest -q
Set-Location ..
```

## Frontend Test Execution

```powershell
Set-Location frontend
npm test
Set-Location ..
```

## Frontend Build

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

## Record Outputs Into Evidence Files

Create an evidence output directory under the allowed runtime spec area if the package scope permits evidence file output:

```powershell
New-Item -ItemType Directory -Force -Path 'specs\runtime\evidence_outputs' | Out-Null
```

Record repository state:

```powershell
git status --short --untracked-files=all *> 'specs\runtime\evidence_outputs\git-status.txt'
git rev-parse HEAD *> 'specs\runtime\evidence_outputs\head.txt'
git log --oneline -3 *> 'specs\runtime\evidence_outputs\git-log.txt'
```

Record backend route listing:

```powershell
Push-Location backend
python -c "from app.main import app; [print(','.join(sorted(getattr(route, 'methods', []) or [])) + ' ' + getattr(route, 'path', '') + ' ' + getattr(route, 'name', type(route).__name__)) for route in app.routes]" *> '..\specs\runtime\evidence_outputs\backend-routes.txt'
Pop-Location
```

Record backend tests:

```powershell
Push-Location backend
python -m pytest --collect-only -q *> '..\specs\runtime\evidence_outputs\backend-pytest-collect.txt'
python -m pytest -q *> '..\specs\runtime\evidence_outputs\backend-pytest.txt'
Pop-Location
```

Record frontend tests and build:

```powershell
Push-Location frontend
npm test *> '..\specs\runtime\evidence_outputs\frontend-npm-test.txt'
npm run build *> '..\specs\runtime\evidence_outputs\frontend-npm-build.txt'
Pop-Location
```

Record final status:

```powershell
git status --short --untracked-files=all *> 'specs\runtime\evidence_outputs\final-git-status.txt'
```

Evidence files are optional package artifacts and must be created only when the active package allows writing under the selected evidence directory.
