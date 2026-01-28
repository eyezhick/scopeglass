# When an object turns into a clause

> The editor knew the author **was** exhausted.

At *the author*, there are two plausible continuations: the editor knew a person,
or the editor knew something about that person. *Was* resolves the local ambiguity
in favor of the second interpretation. This is called NP/S ambiguity: a noun
phrase (NP) can initially look like the object of *knew*, but becomes the subject
of a sentence (S) embedded under it.

Scopeglass crosses the verb's complement options with an overt *that* cue:

| Condition | Context | Critical region |
| --- | --- | --- |
| Ambiguous, no cue | The editor knew the author | **was** |
| Ambiguous, cue | The editor knew that the author | **was** |
| Clause-selecting control, no cue | The editor insisted the author | **was** |
| Clause-selecting control, cue | The editor insisted that the author | **was** |

The interaction is:

```text
[S(ambiguous, absent) − S(ambiguous, that)]
  − [S(control, absent) − S(control, that)]
```

Positive values mean that *that* reduces critical-region surprisal more after
the NP/S-ambiguous verb. The control subtracts the complementizer benefit measured after the control verb;
it cannot remove every difference between the matrix verbs. *Insisted* is a
shared control across all frames, so these twelve lexical frames are not twelve
independent samples of control-verb vocabulary. The amount of object bias also
varies across the ambiguous verbs.

This is an exploratory extension inspired by the targeted ambiguity studies in
[Futrell et al. (2019)](https://aclanthology.org/N19-1004/) and
[Arehalli et al. (2022)](https://aclanthology.org/2022.conll-1.20/).
The sentences are newly authored, not replications of their materials.

NP/S complements the original NP/Z suite. In NP/Z, the parser has to close the
subordinate clause and start a main clause. In NP/S, the matrix verb's complement
turns out to be a clause rather than a noun phrase. The two contrasts need not
have equal magnitude, even within a single model.

```sh
scopeglass stimuli --experiment np_s > np-s.jsonl
scopeglass run --backend hf --experiment np_s --out runs/np-s
```

The run scores only the bold region, including every subword token that makes
it up. The remainder of each sentence is displayed for interpretation, not used
to compute the critical-region score. No human judgments or reading times have
been collected for these materials.
