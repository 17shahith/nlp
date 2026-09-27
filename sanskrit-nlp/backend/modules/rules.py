"""
# SUB-TASK 4: Basic Sanskrit Grammar Rules

A small, fully explicit if/else rule engine. Every rule is a plain
Python function wrapped in a `Rule` object with an id, a human-readable
name/description (shown on the Rules page), and a `hard` flag: a failed
hard rule blocks sentence generation, a failed soft rule is a warning
that still allows generation. Rules never "fix" a violation -- they only
report it. The engine runs every rule and returns every result, so the
frontend can show a full ✓/✗ checklist.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from models import RuleResult
from modules.role_assigner import WordSlot

# Sanskrit person marker used only for rule messages (not stored data).
_PERSON_NAME = {1: "1st person", 2: "2nd person", 3: "3rd person"}


@dataclass
class RuleContext:
    """Everything a rule needs to evaluate the current sentence attempt."""

    slots: list[WordSlot]
    unknown_tokens: list[str]

    def by_role(self, role: str) -> list[WordSlot]:
        return [s for s in self.slots if s.role == role]

    @property
    def verbs(self) -> list[WordSlot]:
        return [s for s in self.slots if s.category == "Verb"]

    @property
    def subjects(self) -> list[WordSlot]:
        return self.by_role("Subject")

    @property
    def objects(self) -> list[WordSlot]:
        return self.by_role("Object")

    @property
    def adjectives(self) -> list[WordSlot]:
        return self.by_role("Adjective")


@dataclass
class Rule:
    id: str
    name: str
    description: str
    check: Callable[[RuleContext], RuleResult]
    hard: bool = True


def _r1_verb_presence(ctx: RuleContext) -> RuleResult:
    verbs = ctx.verbs
    if len(verbs) == 1:
        return RuleResult(id="R1", name="Verb presence", passed=True,
                           message="Exactly one verb found.")
    if len(verbs) == 0:
        return RuleResult(id="R1", name="Verb presence", passed=False,
                           message="Cannot generate sentence: no verb found.")
    return RuleResult(id="R1", name="Verb presence", passed=False,
                       message=f"Cannot generate sentence: {len(verbs)} verbs found, exactly one is required.")


def _r2_subject_presence(ctx: RuleContext) -> RuleResult:
    if ctx.subjects:
        return RuleResult(id="R2", name="Subject presence", passed=True,
                           message="A subject was found.")
    return RuleResult(id="R2", name="Subject presence", passed=False,
                       message="Subject is required. Please provide a subject, e.g., boy, play.")


def _r3_subject_case(ctx: RuleContext) -> RuleResult:
    for s in ctx.subjects:
        if s.chosen_case not in (None, "nominative"):
            return RuleResult(id="R3", name="Subject case", passed=False,
                               message=f"'{s.token}' is used as Subject but is in {s.chosen_case} case, "
                                       f"not nominative (prathama vibhakti).")
    return RuleResult(id="R3", name="Subject case", passed=True,
                       message="Subject is in the nominative (prathama vibhakti).")


def _r4_object_case(ctx: RuleContext) -> RuleResult:
    for s in ctx.objects:
        if s.chosen_case not in (None, "accusative"):
            return RuleResult(id="R4", name="Object case", passed=False,
                               message=f"'{s.token}' is used as Object but is in {s.chosen_case} case, "
                                       f"not accusative (dvitiya vibhakti).")
    return RuleResult(id="R4", name="Object case", passed=True,
                       message="Object (if any) is in the accusative (dvitiya vibhakti).")


def _r5_number_agreement(ctx: RuleContext) -> RuleResult:
    if not ctx.subjects or not ctx.verbs:
        return RuleResult(id="R5", name="Subject-verb number agreement", passed=True,
                           message="Skipped (requires both a subject and a verb).")
    subject, verb = ctx.subjects[0], ctx.verbs[0]
    if subject.chosen_number == verb.chosen_number:
        return RuleResult(id="R5", name="Subject-verb number agreement", passed=True,
                           message=f"Subject and verb agree in number ({subject.chosen_number}).")
    return RuleResult(id="R5", name="Subject-verb number agreement", passed=False,
                       message=f"Subject '{subject.token}' is {subject.chosen_number} but "
                               f"verb '{verb.token}' is {verb.chosen_number}.")


def _r6_person_agreement(ctx: RuleContext) -> RuleResult:
    if not ctx.subjects or not ctx.verbs:
        return RuleResult(id="R6", name="Subject-verb person agreement", passed=True,
                           message="Skipped (requires both a subject and a verb).")
    subject, verb = ctx.subjects[0], ctx.verbs[0]
    expected_person = subject.chosen_person or 3
    actual_person = verb.chosen_person or 3
    if expected_person == actual_person:
        return RuleResult(id="R6", name="Subject-verb person agreement", passed=True,
                           message=f"Subject and verb agree in person ({_PERSON_NAME[expected_person]}).")
    return RuleResult(id="R6", name="Subject-verb person agreement", passed=False,
                       message=f"Subject '{subject.token}' requires a {_PERSON_NAME[expected_person]} verb, "
                               f"but '{verb.token}' is {_PERSON_NAME[actual_person]}.")


def _r7_transitivity(ctx: RuleContext) -> RuleResult:
    if not ctx.verbs:
        return RuleResult(id="R7", name="Transitivity", passed=True,
                           message="Skipped (no verb).")
    verb = ctx.verbs[0]
    transitive = verb.match.word_doc.get("transitive")
    has_object = bool(ctx.objects)
    if transitive is False and has_object:
        return RuleResult(id="R7", name="Transitivity", passed=False,
                           message=f"'{verb.token}' is intransitive and cannot take an object "
                                   f"('{ctx.objects[0].token}').")
    if transitive is True and not has_object:
        return RuleResult(id="R7", name="Transitivity", passed=True, hard=False,
                           message=f"'{verb.token}' is usually transitive; generating a "
                                   f"Subject + Verb sentence with no object.")
    return RuleResult(id="R7", name="Transitivity", passed=True,
                       message="Verb transitivity matches object usage.")


def _r8_adjective_agreement(ctx: RuleContext) -> RuleResult:
    slots_by_index = {s.index: s for s in ctx.slots}
    for adj in ctx.adjectives:
        target = slots_by_index.get(adj.modifies) if adj.modifies is not None else None
        if target is None:
            return RuleResult(id="R8", name="Adjective-noun agreement", passed=False,
                               message=f"Adjective '{adj.token}' has no noun to modify.")
        if adj.chosen_gender != target.chosen_gender:
            return RuleResult(id="R8", name="Adjective-noun agreement", passed=False,
                               message=f"Adjective '{adj.token}' is {adj.chosen_gender} but its "
                                       f"noun '{target.token}' is {target.chosen_gender}.")
        if adj.chosen_case != target.chosen_case or adj.chosen_number != target.chosen_number:
            return RuleResult(id="R8", name="Adjective-noun agreement", passed=False,
                               message=f"Adjective '{adj.token}' does not match '{target.token}' in "
                                       f"case/number.")
    return RuleResult(id="R8", name="Adjective-noun agreement", passed=True,
                       message="Every adjective agrees with its noun in gender, case, and number.")


def _r9_no_duplicate_roles(ctx: RuleContext) -> RuleResult:
    seen: dict[str, str] = {}
    for s in ctx.slots:
        if s.role not in ("Subject", "Object", "Verb"):
            continue
        lemma = s.match.lemma
        if lemma in seen and seen[lemma] != s.role:
            return RuleResult(id="R9", name="No duplicate roles", passed=False,
                               message=f"'{s.token}' cannot be both {seen[lemma]} and {s.role}.")
        seen[lemma] = s.role
    return RuleResult(id="R9", name="No duplicate roles", passed=True,
                       message="No word fills two roles at once.")


def _r10_known_words(ctx: RuleContext) -> RuleResult:
    if not ctx.unknown_tokens:
        return RuleResult(id="R10", name="Known words only", passed=True,
                           message="Every word was found in the vocabulary.")
    words = ", ".join(f"'{t}'" for t in ctx.unknown_tokens)
    return RuleResult(id="R10", name="Known words only", passed=False,
                       message=f"Unknown word(s): {words}. Not present in the vocabulary.")


RULES: list[Rule] = [
    Rule("R1", "Verb presence", "Exactly one verb is required per sentence.", _r1_verb_presence),
    Rule("R2", "Subject presence", "At least one Subject (noun or pronoun) is required.", _r2_subject_presence),
    Rule("R3", "Subject case", "The Subject must be in the nominative (prathama vibhakti).", _r3_subject_case),
    Rule("R4", "Object case", "The Object (if any) must be in the accusative (dvitiya vibhakti).", _r4_object_case),
    Rule("R5", "Subject-verb number agreement",
         "The verb's number must match the subject's number (singular/dual/plural).", _r5_number_agreement),
    Rule("R6", "Subject-verb person agreement",
         "अहम् requires a 1st person verb, त्वम् a 2nd person verb, all others a 3rd person verb.",
         _r6_person_agreement),
    Rule("R7", "Transitivity",
         "An intransitive verb cannot take an object; a transitive verb without an object is a warning.",
         _r7_transitivity),
    Rule("R8", "Adjective-noun agreement",
         "An adjective must match its noun's gender, case, and number.", _r8_adjective_agreement),
    Rule("R9", "No duplicate roles", "The same word cannot fill two roles in one sentence.", _r9_no_duplicate_roles),
    Rule("R10", "Known words only", "Every input word must exist in the vocabulary.", _r10_known_words),
]


def run_all(ctx: RuleContext) -> list[RuleResult]:
    """Run every rule against the context and return all results, in order."""
    results = []
    for rule in RULES:
        result = rule.check(ctx)
        result.hard = rule.hard
        results.append(result)
    return results


def hard_failures(results: list[RuleResult]) -> list[RuleResult]:
    """Return only the results that represent a blocking (non-warning) failure."""
    by_id = {r.id: r for r in RULES}
    failures = []
    for result in results:
        if result.passed:
            continue
        rule = by_id.get(result.id)
        if rule is None or rule.hard:
            failures.append(result)
    return failures
