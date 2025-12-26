# AI Director

are things like this good or bad?: Example 1: The "Dead" Informant The Situation: A spy named Marcus was assassinated in the Borderlands (Objective Fact). The "Blind" Director (Standard AI): Sees Marcus is dead. Immediately schedules a "Funeral Event" in the city or spawns a "New Spy" to replace him because the "Spy slot" is empty. The "Epistemically Aware" Director: 1. Sees Marcus is dead (Layer 1). 2. Sees the Faction Leader still believes Marcus is "On Mission" with 90% confidence (Layer 3). 3. The Drama Opportunity: Instead of a funeral, the Director schedules a "Deceptive Correspondence" event. An enemy intercepts Marcus’s seal and sends a false "Information Artifact" (Layer 2) to the Leader. 4. The Result: The Leader acts on a false belief, sending reinforcements into a trap. The drama comes from the gap between reality and belief. Example 2: The Ghost of the Ruins The Situation: Elias explored the Ruins and found nothing but old pottery (Objective Fact). However, due to his "High Anxiety" trait, he misidentified a shadow as a "Void Stalker" (False Artifact). The "Blind" Director: Sees the Ruins are empty. Does nothing because there is no "threat" to manage. The "Epistemically Aware" Director: 1. Sees Elias has returned to the Sanctuary with a CONVINCED belief in a monster (Layer 3). 2. Sees this belief spreading to Maria via "Gossip" (Perception System). 3. The Drama Opportunity: The Director triggers a "Mass Panic" world event. Even though there is no monster, the town starts boarding up windows and hoarding food. 4. The Result: The simulation creates an economic crisis (high food prices) based entirely on a lie. The "monster" is a social reality, even if it's a physical myth. Example 3: The Contradictory Map The Situation: A hidden treasure is located in the North (Objective Fact). The "Blind" Director: Creates a quest where an NPC gives the player/character a map to the North. The "Epistemically Aware" Director: 1. Searches for "Contradiction Density." 2. Finds that Faction A believes the treasure is North, but Faction B has a "Deduction Artifact" (Layer 2) suggesting it's South. 3. The Drama Opportunity: The Director schedules a "Collision Course" event at a neutral tavern. 4. The Result: Characters from both factions meet. Because their Belief Graphs are in total contradiction, the Director triggers a "Heated Debate" or "Brawl" action. The story isn't about the treasure; it's about the Information Asymmetry between two groups who both think they are right.

## High-level verdict on your three examples
Example	Design quality	Why
Dead Informant	✅ Excellent	Uses misinformation, not retcon
Ghost of the Ruins	⚠️ Powerful but risky	Director escalates belief into world effects
Contradictory Map	✅ Excellent	Conflict emerges from belief asymmetry

Now let’s go deeper, because the nuance matters.

##❌ Bad Director behavior

Creates facts directly
Resolves uncertainty
Forces emotional states
Ensures “story beats”
Treats belief as cosmetic

### Bad Example: Ghost of the Ruins
This one is brilliant, but it crosses a boundary that needs guarding.
The risk is here:
“The Director triggers a ‘Mass Panic’ world event.”
If “Mass Panic” is:
a hard override of NPC behavior → ❌ dangerous
a belief-driven emergent cascade → ✅ excellent
Safe version
The Director:
Increases rumor spread probability
Lowers skepticism thresholds
Allows prices to respond to demand spikes
The panic emerges.
Unsafe version
The Director:
Forces the city into panic state regardless of beliefs
Spawns economic collapse directly
That turns the Director into a god.
Rule:
The Director may amplify signals, but must never declare outcomes.

##✅ Good Director behavior
Creates artifacts
Modulates information flow
Identifies epistemic instability
Schedules plausible interactions
Lets consequences be uncertain

'''
A formal rule you should encode
'''
'''
The Director may only act on Layer 2.
It may observe Layer 1 and Layer 3,
but it may only create or route Information Artifacts or Event Opportunities.
'''