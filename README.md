# Agent Based Model Dist Kiss


### Brief description of contents
The model can be found in ```model_code/distkiss_model.py```. Some functions used in the model are outsourced into other files, these are ```model_code/graph_helpers.py```, ```model_code/movement.py```, ```model_code/spatial_output_creator.py```. There are several files to run the model with different parameter sets and configurations called ```run_[...].py```.
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


### OUTDATED DESCRIPTION:
The model includes a street network of the city Quakenbrueck located in Lower Saxony, Germany. Several agents are created at setup. 
Each agents gets an origin and destination point in the city center of Quakenbrueck assigned, at least 250m appart from each other. The shortest path from the agents origin nearest node (intersection) to the nearest node of its destination is calculated. 
During each timestep the agent walks with a randomly assigned walking speed between 1-2 m/s. The duration of a timestep is 5 seconds (configurable).
If they pass by a street node during walking they wait until the current timestep is over.
Agents traverse the street network along the shortest path until they reach their destination. Each agent has a random density-tolerance-thrshold between 5-10 assigned. Before the agent walks onto the next street segment it checks whether the amount of agents currently on that street is higher than its density-tolerance-threshold. If so, the agent waits at its position until the numebr is lower than the threshold, else he continues traversing its path. If it has reached the destination it stays at that location. 
The output of the model with paramters set to 50 agents and 20 timesteps currently looks (similar) as shown below: 


https://user-images.githubusercontent.com/18304291/178452162-f5b95d39-ead1-4f77-8a69-caeb81020c15.mp4