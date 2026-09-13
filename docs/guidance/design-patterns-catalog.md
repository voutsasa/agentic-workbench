# Design Patterns Catalog — Agent Guidance

**Provenance: model background** — general knowledge written down, resting on no source in this repo. No design-patterns reference is registered in [`SOURCES.md`](../../SOURCES.md); registering one and rewriting this note against it would put it on firmer footing. See [`README.md`](README.md).

A quick-reference index of the classic object-oriented design patterns, meant to help an agent recognize *"this situation has a well-known shape"* instead of inventing an ad hoc structure. This is background knowledge to draw on, not a checklist to force onto every task — per the project's general stance on avoiding premature abstraction, only reach for a pattern when the trigger genuinely matches, not because a pattern exists.

## Creational — ways to construct objects

| Pattern | Intent | Reach for it when | Watch out |
|---|---|---|---|
| Factory Method | Delegate object creation to a method subclasses can override, instead of calling a constructor directly. | Callers need one of several related object types but shouldn't know which concrete class to instantiate. | Adds an interface/subclass layer — skip it if there's only ever one concrete type. |
| Abstract Factory | Group several factory methods so a caller can create a whole family of related objects consistently. | The app must swap entire families of related objects together (e.g. one UI theme's full widget set). | Overkill if there's only one product family in practice. |
| Builder | Assemble a complex object step by step, separating construction logic from the final representation. | Construction needs many optional parameters/steps, or the same steps must produce different representations. | For simple objects, a plain constructor or config dict is clearer. |
| Prototype | Create new objects by copying an existing instance rather than building from scratch. | Object creation is expensive, or you need copies that vary only slightly from a template instance. | Deep vs. shallow copy semantics need to be explicit or this silently causes shared-state bugs. |
| Singleton | Guarantee a class has exactly one instance and expose a single access point to it. | There's a genuinely unique shared resource (e.g. a connection pool) and multiple instances would be incorrect, not just wasteful. | Frequently overused; it introduces global state and makes testing/parallelism harder — prefer dependency injection where possible. |

## Structural — composing objects and classes into larger units

| Pattern | Intent | Reach for it when | Watch out |
|---|---|---|---|
| Adapter | Convert one interface into another that callers expect. | Integrating a third-party or legacy component whose interface doesn't match what the rest of the code expects. | If you control both sides, it's often better to just align the interfaces than to add an adapter. |
| Bridge | Split an abstraction from its implementation so each can vary independently. | Both "what" and "how" are expected to grow independent variants (e.g. multiple shapes × multiple renderers). | Adds indirection up front — not worth it if only one implementation will ever exist. |
| Composite | Treat individual objects and groups of objects through the same interface. | Modeling part-whole/tree structures where clients shouldn't need to distinguish a leaf from a branch. | Can make it harder to restrict operations that only make sense for one level of the tree. |
| Decorator | Attach additional behavior to an object dynamically by wrapping it. | Behavior needs to be composed at runtime from independent, stackable add-ons, and subclassing would explode combinatorially. | Deep decorator chains get hard to debug/trace — don't reach for this over a simple flag or conditional. |
| Facade | Provide a single simplified interface over a more complex subsystem. | Callers only need a narrow slice of a large subsystem's capability and shouldn't be coupled to its internals. | Don't let the facade become a second, parallel API surface that has to be kept in sync with the subsystem. |
| Flyweight | Share the immutable parts of many similar objects to reduce memory footprint. | A very large number of fine-grained objects share most of their state (e.g. glyphs, map tiles). | Only worth the complexity at genuine scale — premature use adds indirection for no real saving. |
| Proxy | Provide a stand-in for another object to control access to it (lazy loading, access control, caching, remote calls). | Something needs to sit transparently in front of a real object — deferring cost, checking permissions, or crossing a process/network boundary. | Easy to accidentally hide expensive or failure-prone operations behind what looks like a cheap local call. |

## Behavioral — communication and responsibility between objects

| Pattern | Intent | Reach for it when | Watch out |
|---|---|---|---|
| Chain of Responsibility | Pass a request along a chain of handlers until one handles it. | An open-ended set of handlers might apply, and the sender shouldn't need to know which one will act. | If exactly one handler should always run, a chain adds indirection without benefit. |
| Command | Encapsulate a request (and its parameters) as an object, so it can be queued, logged, or undone. | You need to parameterize actions, queue/schedule them, or support undo/redo. | Not needed for simple, immediate, one-shot calls — adds ceremony for no gain there. |
| Iterator | Provide a way to traverse a collection's elements without exposing its internal structure. | A custom collection needs uniform, sequential access regardless of its internal storage. | Most languages/frameworks already provide this — only hand-roll it for a genuinely custom collection type. |
| Mediator | Centralize how a set of objects communicate, so they don't reference each other directly. | Many objects interact in a tangled many-to-many way and that web of references is becoming hard to follow. | The mediator itself can become an unmanageable "god object" if it absorbs too much logic. |
| Memento | Capture and externalize an object's internal state so it can be restored later, without violating encapsulation. | You need undo/rollback/snapshot support for an object's state. | Storing full snapshots can be memory-heavy for large or frequently-changing state. |
| Observer | Let dependents subscribe to and get notified of changes in a subject, without tight coupling between them. | Multiple parts of the system need to react to a change in one place (events, pub/sub, reactive UI state). | Watch for unclear update ordering and hard-to-trace notification chains ("spooky action at a distance"). |
| State | Let an object change its behavior when its internal state changes, as if it changed class. | An object's behavior is a large conditional keyed off a mode/status field, and that mode changes over time. | For a small, stable set of states, a plain enum + switch is often simpler than the full pattern. |
| Strategy | Define a family of interchangeable algorithms and select one at runtime. | Several algorithms solve the same problem and the caller should be able to pick or swap between them. | If there's really only one implementation and no plan for more, a strategy interface is unneeded indirection. |
| Template Method | Define the skeleton of an algorithm in a base class, letting subclasses override specific steps. | Several variants share the same overall sequence of steps but differ in a few specific ones. | Overriding hooks in a base class is a form of inheritance coupling — composition (Strategy) is often more flexible. |
| Visitor | Separate an algorithm from the object structure it operates on by having elements "accept" a visitor. | You need to add new operations over a stable set of object types without modifying those types repeatedly. | Adding a new element type requires updating every visitor — the trade-off runs the opposite way from Strategy. |

## Using this as an agent

When a design decision feels like it needs "some structure," check this table for a matching trigger before reaching for a pattern by name. If nothing here matches the actual problem, that's a signal to write the straightforward version rather than force-fitting a pattern.
