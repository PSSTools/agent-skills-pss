# Action inferencing

*Domain: activity. LRM Clause 14.*

**The tool will add actions to your scenario that you did not write.** If a traversed action has
an unbound `input`, the tool infers an action that produces the required object — and then
recursively satisfies *that* action's inputs. This is PSS's most powerful feature and its most
surprising one.

Understanding it is not optional: it determines both what your test actually contains and why a
partially specified scenario sometimes fails to solve.

## When you are writing this

- You wrote an activity and the generated scenario has more actions than you traversed.
- The solver reports there is no legal scenario, and the activity looks fine.
- You want to write intent (`do transfer;`) and let the tool arrange the prerequisites.
- You want to *prevent* the tool from filling in the gaps.

## Decide

| You want… | Do |
|---|---|
| the tool to supply prerequisites | leave the `input` unbound — this is the default |
| a specific producer | traverse it explicitly and bind: `bind a.out c.in;` or connect via constraints |
| **no** inference into a region | wrap it in `atomic { }` — inferred actions are never in an atomic set |
| to narrow which actions can be inferred | scope the **pool** — inference only considers actions bound to the same pool |
| to steer which producer is chosen | constrain the object's fields; incompatible constraints force a *different* (possibly new) producer |
| a fully directed test | traverse everything and constrain every field |

**The pool is the control surface.** The set of actions from which a traversal may be inferred
is determined by **pool binding** (§14.2). If you want to keep two subsystems from filling in
each other's inputs, give them separate pools — not separate activities.

## Canonical form

```pss
component pss_top {
    buffer data_buff_s { rand int val; }
    pool data_buff_s data_mem;
    bind data_mem *;

    action A_a { output data_buff_s dout; }
    action B_a { output data_buff_s dout; }
    action C_a { input  data_buff_s din;  }

    // Partial specification: only the intent is stated.
    action root_a {
        activity {
            do C_a;              // C_a needs a data_buff_s...
        }                        // ...so A_a or B_a is INFERRED and scheduled before it
    }

    // Fully specified: nothing is inferred.
    action directed_a {
        A_a a;
        C_a c;
        activity {
            a;
            c;
        }
        constraint c.din.val == a.dout.val;   // relate them explicitly
    }

    // Inference deliberately excluded.
    action protected_a {
        activity {
            atomic {
                do A_a;
                do C_a;
            }
        }
    }
}
```

## Rules

- **Inference completes a partial specification.** Beginning at a root action, the tool
  introduces additional action traversals as needed so that every flow-object requirement is
  satisfied and every constraint holds (Clause 14).
- **Only actual action types can be inferred.** A *generic* template type may not be inferred
  (§10.5).
- **Pool binding bounds the candidate set** (§14.2). An action bound to a different pool of the
  same type is not a candidate.
- **Data constraints affect which action is inferred** (§14.3). If the constraints on a
  traversal's input are incompatible with the outputs of the explicitly traversed producers,
  the tool infers *another* producer instance rather than failing.
- **Inference is recursive.** An inferred action's own inputs are satisfied the same way.
- **Object kind still governs scheduling.** An inferred `buffer` producer completes before the
  consumer; an inferred `stream` producer runs in parallel with it; state rules apply as usual.
- **`pre_solve`/`post_solve` ordering applies identically to inferred actions** (§13.4.12,
  restated in Clause 14): the evaluation order conforms to the scheduling relations — if an
  action is scheduled before another, its solve execs are evaluated first.
- **Backtracking is not performed across exec blocks.** An assignment in an exec to an
  attribute that appears in a constraint can therefore produce an unsatisfied-constraint error.
  This applies to inferred actions exactly as to explicit ones.
- **`atomic` blocks exclude inference** — inferred actions are never members of an atomic set
  (§11.3.7).

## Gotchas

**Being surprised by extra actions in the test.** This is inference working. If it is unwanted,
the fix is `atomic { }`, a narrower pool, or explicit traversal — not more constraints.
*Tier 4* — nothing reports it; you notice it in the generated test.

**"No legal scenario" when nothing can be inferred.**
```pss
action C_a { input data_buff_s din; }    // and NO action anywhere outputs data_buff_s
```
*Tier 3.* Check, in order: does *any* action output that type; is it bound to the **same pool**;
is that pool bound to a component the consumer can reach; are the data constraints satisfiable
by that producer.

**Assuming an unbound input will use an action you traversed.** It may — or the tool may infer
a *second* instance of the same type, because your traversal's output was already consumed or
its constraints don't match. If you need them connected, say so: an explicit `bind` in the
activity, or a constraint relating the two objects.
*Tier 4.*

**Adding a constraint and silently doubling the action count.**
```pss
do C_a with { din.val > 100; };   // if no traversed producer can make val>100,
                                  // a new producer is inferred, not an error
```
*Tier 4* — the model still solves, with more actions than expected.

**Expecting `atomic` to prevent all extra actions.** It prevents inferred actions from
*interleaving into the block's scheduling structure*; it does not stop the block's own unbound
inputs from being satisfied. Bind them explicitly if that matters.
*Tier 4.*

**Writing to a constrained attribute from a solve exec.** No backtracking happens across exec
blocks, so an assignment that contradicts a constraint is an error rather than a re-solve.
*Tier 3.*

**Relying on a template action being inferred.** Generic template types are excluded (§10.5) —
the failure reads as "nothing can produce this".
*Tier 3.*

**One shared pool across the whole model.** `bind p *;` at `pss_top` makes every action of that
type a candidate for every consumer, everywhere. Convenient at first, then the source of
scenarios that reach across subsystems in ways nobody intended.
*Tier 4.*

## See also

- `../structural/06-pools-and-binding.md` — the mechanism that scopes inference.
- `../structural/04-flow-objects.md` — what each object kind implies for the inferred schedule.
- `01-activities.md` — `atomic`, explicit traversal, and `bind` in an activity.
- `../constraints/03-randomization.md` — §13.4.12 exec evaluation ordering, and lookahead.
- `../../playbooks/10-diagnose.md` — "no legal scenario" triage.
