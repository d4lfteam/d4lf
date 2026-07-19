# Refactor D4LF into Deep Capability Modules

Status: ready-for-agent

## Problem Statement

D4LF has grown through repeated changes and now takes too much effort to understand, modify, and
verify safely. Large Python files mix unrelated responsibilities, capability code is scattered
across broad technical packages, and shared helper buckets obscure ownership. Twenty-nine source
files and eight test files exceed the new 300-line limit. The test tree also does not consistently
show which source module owns each unit test.

This makes maintenance risky even though the application's behavior is established and must remain
unchanged. The refactor must improve locality and readability without increasing production code,
introducing compatibility layers, or replacing large files with many shallow pass-through modules.

## Solution

Reorganize D4LF into capability-first deep modules with small package interfaces and cohesive private
implementations. Review every source module, retain well-placed cohesive code, move or split code
whose ownership is unclear, deduplicate repeated behavior, and delete code that is unused anywhere
in the repository.

Complete the source refactor in dependency order and verify it before restructuring tests. Then
create an exact mirrored unit-test tree, add package-interface and cross-capability integration
coverage, move reusable test data out of Python modules, and enforce the 300-line limit throughout
the Python source and test trees.

## User Stories

1. As a D4LF user, I want item filtering behavior to remain unchanged, so that existing profiles keep producing the same keep and junk decisions.
1. As a D4LF user, I want vision mode fast to behave as before, so that hovered items still receive the expected tooltip-level result.
1. As a D4LF user, I want vision mode with highlighting to behave as before, so that matched affixes still receive the expected affix markers.
1. As a D4LF user, I want profile loading and saving to preserve existing semantics, so that my stored profiles remain usable.
1. As a D4LF user, I want imported profiles and Paragon payloads to remain equivalent, so that refactoring does not alter my builds.
1. As a D4LF user, I want hotkeys, overlays, pointer movement, and inventory automation to remain unchanged, so that established workflows continue to work.
1. As a maintainer, I want every Python file in the source and test trees to contain at most 300 physical lines, so that files remain reviewable.
1. As a maintainer, I want the line-limit command documented with the normal validation commands, so that contributors run it consistently.
1. As a maintainer, I want code organized by product capability, so that related behavior and knowledge remain local.
1. As a maintainer, I want each deep module to expose a small interface, so that callers do not need to understand its implementation.
1. As a maintainer, I want package interfaces to be explicit, so that cross-package dependencies are easy to identify.
1. As a maintainer, I want implementation modules to remain private across packages, so that internal refactors have limited impact.
1. As a maintainer, I want capability-specific GUI code to live with its capability, so that behavior and presentation do not drift into separate ownership silos.
1. As a maintainer, I want only genuinely shared desktop code in the desktop module, so that it does not become another generic GUI bucket.
1. As a maintainer, I want platform variation represented by real adapter seams, so that Windows and no-op behavior remain explicit without hypothetical abstractions.
1. As a maintainer, I want generic helper and model buckets reduced, so that every retained abstraction earns its place through reuse or depth.
1. As a maintainer, I want repeated importer behavior consolidated behind a normalized interface, so that source adapters contain only source-specific behavior.
1. As a maintainer, I want perception behavior localized, so that screenshot, template, item-description, image, and TTS changes can be reasoned about together.
1. As a maintainer, I want automation behavior localized, so that window, input, inventory, and pointer operations share a coherent interface.
1. As a maintainer, I want Paragon transformation and overlay behavior to preserve the glossary's payload, progression-step, board, and rotation semantics.
1. As a maintainer, I want unused in-project code deleted, so that obsolete paths do not compete with active behavior.
1. As a maintainer, I want Windows-only code retained when it is used, so that static analysis on macOS does not remove production behavior.
1. As a maintainer, I want production Python LOC to remain at or below its pre-refactor baseline, so that restructuring reduces or maintains code volume.
1. As a contributor, I want every source module to have a predictable mirrored unit-test file, so that I can locate its tests immediately.
1. As a contributor, I want every package initializer to have an `init_test.py`, so that package interfaces are verified consistently.
1. As a contributor, I want unit tests to cover module behavior directly, so that focused failures identify the owning implementation module.
1. As a contributor, I want package-interface tests to exercise deep-module behavior, so that callers and tests rely on the same seam.
1. As a contributor, I want cross-capability scenarios isolated as integration tests, so that collaborations are distinct from unit ownership.
1. As a contributor, I want reusable test data stored as non-Python fixtures, so that test support modules do not break the source-to-test mapping.
1. As a contributor, I want duplicate tests and fixtures consolidated, so that behavior is specified once at the highest useful seam.
1. As a contributor, I want source restructuring completed before test restructuring, so that the final test layout mirrors a stable architecture.
1. As a contributor, I want temporary source-phase test reference edits removed, so that the final suite contains no migration scaffolding.
1. As a reviewer, I want the refactor delivered in dependency-ordered waves, so that regressions can be isolated to a capability.
1. As a reviewer, I want high-risk seams considered through multiple interface designs, so that the chosen modules provide depth rather than merely moving code.
1. As a reviewer, I want existing ADR and domain glossary decisions preserved, so that structural work does not silently change business behavior.
1. As a release maintainer, I want local formatting, lint, line-limit, and non-Selenium tests to pass, so that the refactor meets repository quality gates.
1. As a release maintainer, I want Windows CI to pass, so that Windows-only TTS, overlay, and UI behavior receives its available automated coverage.
1. As a release maintainer, I want the Windows executable build to succeed, so that package moves do not break PyInstaller or release wiring.

## Implementation Decisions

- Keep `src` as the Python import package. Renaming the package root would add widespread mechanical
  churn without improving runtime behavior or the chosen module seams.
- Organize code into capability-first deep modules covering item behavior, profiles, settings,
  importing, perception, Paragon, automation, loot filtering, shared desktop behavior, application
  composition, and developer tools.
- Keep capability-specific GUI behavior with its capability. The desktop module owns only shared
  Qt/Tk widgets, dialogs, themes, UI-thread handling, and shell composition.
- Each capability package's `__init__.py` is its intentionally small external interface. Cross-package
  callers use this interface rather than importing another package's implementation modules.
- Internal implementation files may be split as needed to remain cohesive and under 300 physical
  lines. Splits based only on line ranges and shallow forwarding modules are not acceptable.
- Preserve real adapter seams where behavior varies, including Windows and no-op TTS and window
  implementations. Do not introduce interfaces for hypothetical variation.
- Keep the existing `ProfileSession` seam free from PyQt dependencies.
- Preserve all glossary and ADR behavior for profiles, item rarity, rarity filters, sigil rules,
  tribute filters, Paragon data, hotkey bindings, vision modes, and affix markers.
- Review every source module, including modules already under 300 lines. Change only modules whose
  ownership, interface, duplication, or placement demonstrably improves.
- Delete code that is unused anywhere in the repository. Before deletion, account for dynamic
  imports, application entry points, build configuration, and Windows-only execution paths.
- Do not retain old import paths or add compatibility forwarding modules. Update all repository
  imports, patch targets, package metadata, and build references to the final structure.
- Refactor in dependency-ordered waves: inventory and seams; item/profile/settings foundations;
  importing/perception/Paragon; automation/loot; desktop/application/tools; source verification;
  test migration; final acceptance.
- During source waves, tests may receive only the import and patch-target updates needed to continue
  behavior verification. Test relocation, splitting, renaming, and cleanup occur only after the
  source phase is complete and verified.
- The source phase is complete only when every source Python file is at most 300 physical lines, the
  behavior suite passes, and source Python LOC does not exceed the corrected 26,229-line baseline
  recorded in ADR 0006, unless an explicit offset is approved.
- The hard 300-line policy applies to Python files in the source and test trees, matching the
  repository guard. It does not expand to C++, hooks, documentation, or configuration in this work.
- Document the line-limit command alongside the repository's normal validation commands.
- Record the capability-first deep-module architecture in an ADR because it is a broad, costly-to-
  reverse trade-off that future maintainers need to understand.
- Update the domain glossary only if the refactor exposes and resolves an actual terminology
  conflict. Structural implementation details do not belong in the glossary.
- After the source structure is frozen, map each source module to one unit-test file using
  `<module>_test.py`; map every package initializer, including the root initializer, to
  `init_test.py`.
- Keep only mirrored unit-test files and `conftest.py` files in the unit-test tree. Store reusable
  case data as non-Python fixtures and place cross-capability tests in a separate integration tree.
- Test LOC may increase where required for missing unit, package-interface, or integration coverage,
  but duplicate tests and fixtures should be removed.

## Testing Decisions

- A good test asserts observable behavior, results, state transitions, side effects, invariants, and
  documented errors at the highest useful seam. It does not assert incidental call order, private
  data layout, or extraction mechanics.
- Every source file receives a mirrored unit-test file. These tests may import implementation
  modules directly, but they test the module's observable behavior rather than how that behavior is
  internally implemented.
- Every package receives an `init_test.py` that exercises its exported deep-module interface.
  Export-name assertions alone are insufficient when meaningful behavior can be tested through the
  interface.
- Integration tests exercise collaborations across multiple deep-module interfaces. They do not
  reach through package interfaces to coordinate private implementation modules.
- Existing tests are the behavioral baseline and should be migrated rather than discarded. Current
  prior art includes focused tests for item filtering and description parsing, profile documents and
  sessions, importer adapters and pipelines, GUI tabs and windows, geometry location, automation
  utilities, replay tools, overlays, and Paragon transformation.
- Existing case-heavy parser and filter data should become non-Python fixtures where reuse or size
  makes inline parameterization unsuitable.
- Duplicate tests for the same source behavior should be merged and assigned to the highest useful
  seam. Focused internal tests remain where they add distinct diagnostic value.
- After each source wave, run focused tests for the affected capability and the line guard. At the
  source freeze and final acceptance points, run the complete non-Selenium suite.
- The current macOS baseline is 586 passing tests and 47 skips. A refactor must not explain away a
  regression by changing or deleting an existing behavioral assertion.
- Final local gates are the line guard, all configured prek checks, and the complete non-Selenium
  pytest suite.
- Final platform gates are a successful Windows CI test run and the separately triggered Windows
  PyInstaller build.

## Out of Scope

- New end-user features or deliberate changes to item filtering, profile, importer, Paragon,
  overlay, automation, hotkey, or vision-mode behavior.
- Renaming the `src` import package.
- Backward compatibility for old internal Python import paths.
- Expanding the 300-line guard beyond Python files in the source and test trees.
- Replacing the existing Windows CI and manual build workflows with a different release process.
- Enabling, redesigning, or expanding the Selenium suite.
- Speculative interfaces with only one implementation and no demonstrated variation.
- Rewriting cohesive modules solely for stylistic consistency.

## Further Notes

- The initial line guard reports 29 source violations and 8 test violations.
- The source refactor must finish and pass its acceptance gates before structural test migration
  begins. Minimal test reference changes made during the source phase are temporary and must be
  absorbed into the final mirrored test tree.
- Windows CI and the Windows executable build are both required because macOS skips several
  Windows-only TTS, overlay, and UI tests and cannot validate the packaged application.
- Existing uncommitted changes to the line guard and prek configuration belong to the user and must
  be preserved.
