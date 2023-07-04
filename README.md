# Agent Based Model Dist Kiss


### Brief description of contents
The model can be found in ```model_code/distkiss_abm.py```. Some functions used in the model are outsourced into other files, these are ```model_code/graph_helpers.py```, ```model_code/movement.py```, ```model_code/spatial_output_creator.py```. There are several files to run the model with different parameter sets and configurations called ```run_[...].py```.
An animation of the model can be created by runnning ```model_code/graph_helpers.py```. To perform a sensitivity analysis use the script ```model_code/sensitivity.py```. 

### File structure of the repository
```
project
│   .gitignore    
│   ENV.yml
│   README.md
│
└───animation_output
│   │   example_animation.html
│   
└───input_data
│   │   quakenbrueck.gpkg
│   │   quakenbrueck_slides.gpkg
│   │   quakenbrueck_street_width.gpkg (currently used input file)
│
└───model_code
│   │   animate_model.py (creates animation of model)
│   │   distkiss_abm.py (the actual model code)
│   │   graph_helpers.py (helper functions for model)
│   │   movement.py (helper functions for model)
│   │   run_experiment.py (script to run AgentPy Experiments)
│   │   run_single_model_run.py (script to run a single model run)
│   │   run_with_optimal_parameters.py (script to run the model with calibrated parameter set)
│   │   sensitivity.py (script to run model & execute sensitivity analysis)
│   │   sensitivity_plots.py (helper unctions for sensitivity result visualizations)
│   │   spatial_output_creator.py (helper functions for saving model outputs)
|   |   dsg_scenes.py (helper functions for gathering data for POST-REQ to the DSG) 
│
└───postprocessing
│   │   avg_max_densities.py
│   │   diff_max_densities.py
│   │   diff_stats_densities.py
│   │   map_median_density_per_street.py
│   │   map_median_density_per_street_only_no_interventions.py
│   │   mean_densities_by_scenario.py
│   │   mean_densities_by_street_by_scenario.py
│
└───qgis_styles
    │   compliance_location_style.qml
    │   edges_style_conference.qml
    │   ows_style_conference.qml
    │   points_style_conference.qlr
    │   points_style_conference.qml


```

### Running the model

There are several files that can be used to run the model for different purposes. Here a brief overview of what they are made for is given:

1. **run_single_model_run.py** - This is the simplest of all version. The model is run for the scenario of "complex" compliance behavior (agents dynamically decide to comply or not to comply and to reroute) with a default configuration of 200 agents and 720 timesteps (1 hour time equivalent). All outputs are disabled in the parameter set. The model will run, but produce an empty output folder. Output parameters can be set to true, to generate outputs. 

2. **run_with_optimal_parameters.py** - Similar to the **run_single_model_run** but with 2000 agents and model outputs are activated. These are: (1) positions of all agents for all timesteps (2) edges, with pedestrian counts, for all timesteps, (3) compliance nodes and (4) edges with maximum density over all timesteps are created as outputs.

3. **animate_model.py** - This file creates a html animation as output. The animation shows the street network with agents and their positions as dots over time.

4. **run_experiment.py** This is version runs an experiment, where the scenario is varied, between _simple compliance_ (all agents comply with all interventions), _complex compliance_ (agents dynamically decide to comply or not to comply) and _no interventions_ (there are no interventions on the streets). The model is run 10 times (iterations) for each scenario with different model seeds. By default (1) edges, with pedestrian counts, for all timesteps, (2) compliance nodes and (3) edges with maximum density over all timesteps are created as outputs. Additionally, the following outputs are generated in reporters.csv:
```
mean normalized oberserved detour, std of normalized oberserved detour, variance of normalized oberserved detour, mean non-compliance probability, std of non-compliance probability, variance of non-compliance probability, mean compliance probability, std of compliance probability, number of non-compliances, number of compliances, number of no-route-changes, number of random-reroutings, Array of shortest path lengths, Array of total path legngths, Array of normalized observed detours, Array of non-compliance probabilities, Array of compliance probabilities
```

5. **sensitivity.py** This script runs a sensitivity analysis for the model. Default number of agent is 1000 and timesteps are 2000 (~2.7 hours). Unlike in other model runs, weights for compliance function and walking speed is fixed for all agents within a model run. The model is run multiple times systematically varying the parameters. Sample size can be adjusted. Default is 8 (which should be too low to produce valid sensitivity indices!). Default setting is to run each parameter combination for 30 iterations. 

### Extracting Scenes to the Dynamic Scene Generator (DSG)

The model offers the possibility to extract data from situations, when an agent in the model has to decide, whether he wants to reroute or not. This situations are only captured if the probability to stay on the current path ("prop_no_deviate") are inside a specified interval (in our case between 48% and 52%). This interval should be changed, depending on want situations you are interested to capture. Such a situation can occur on an intersection in the street-network.
A Intersection is always related to a node in the graph of the model. The following situations are currently captured in this model:
- Agents that deviate from their current path
- Agents that want to deviate from their current path but then realizing they  would have to move through an street intervention, resulting in rethinking their decision (thus a new probability is calculated)
- Agents that randomly reroute
- Agents that turn around at an intersection (taking the path they came from). This situation is identical to the first mentioned situation.

In this situations the model captures the following data:
- distance of each path going out from that intersection, from the node to the destination of the agent
- streetsign assigned to each edge of the node
- crowdedness of each edge of the node
- degree of the node

All this data is then summarized in a JSON-Object. These Objects can then be send to the [DSG](https://github.com/dist-kiss/dynamic_scene_generator). To decide how many situations should be send, you can change the "scenes_to_generate" parameter in the parameter dictionary in "run_experiment.py".

### OUTDATED DESCRIPTION:
The model includes a street network of the city Quakenbrueck located in Lower Saxony, Germany. Several agents are created at setup. 
Each agents gets an origin and destination point in the city center of Quakenbrueck assigned, at least 250m appart from each other. The shortest path from the agents origin nearest node (intersection) to the nearest node of its destination is calculated. 
During each timestep the agent walks with a randomly assigned walking speed between 1-2 m/s. The duration of a timestep is 5 seconds (configurable).
If they pass by a street node during walking they wait until the current timestep is over.
Agents traverse the street network along the shortest path until they reach their destination. Each agent has a random density-tolerance-thrshold between 5-10 assigned. Before the agent walks onto the next street segment it checks whether the amount of agents currently on that street is higher than its density-tolerance-threshold. If so, the agent waits at its position until the numebr is lower than the threshold, else he continues traversing its path. If it has reached the destination it stays at that location. 
The output of the model with paramters set to 50 agents and 20 timesteps currently looks (similar) as shown below: 


https://user-images.githubusercontent.com/18304291/178452162-f5b95d39-ead1-4f77-8a69-caeb81020c15.mp4
