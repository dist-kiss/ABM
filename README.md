# Agent Based Model Dist Kiss

This repository includes all code and information regarding the ABM. 
There is a file called abm.py which includes the model. 

The model includes a street network of the city Quakenbrueck located in Lower Saxony, Germany. Several agents are created at setup. 
Each agents gets an origin and destination point in the city center of Quakenbrueck assigned, at least 250m appart from each other. The shortest path from the agents origin nearest node (intersection) to the nearest node of its destination is calculated. 
During each timestep the agent walks with a randomly assigned walking speed between 1-2 m/s. The duration of a timestep is 5 seconds (configurable).
If they pass by a street node during walking they wait until the current timestep is over.
Agents traverse the street network along the shortest path until they reach their destination. Each agent has a random density-tolerance-thrshold between 5-10 assigned. Before the agent walks onto the next street segment it checks whether the amount of agents currently on that street is higher than its density-tolerance-threshold. If so, the agent waits at its position until the numebr is lower than the threshold, else he continues traversing its path. If it has reached the destination it stays at that location. 
The output of the model with paramters set to 50 agents and 20 timesteps currently looks (similar) as shown below: 

https://user-images.githubusercontent.com/18304291/141971630-077c91e2-3160-4ff3-b468-6ef6c5ac0d7c.mp4
