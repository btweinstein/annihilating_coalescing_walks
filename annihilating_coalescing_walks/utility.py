import numpy as np
import pandas as pd
import annihilating_coalescing_walks.inflation as acwi
import numpy as np
import statsmodels.api as sm
import gc

def get_log_record_times(max_order, number_per_interval=100):
    if number_per_interval > 200:
        print '200 point is the most that can be done per octave without' \
              'looking at a scale less than O(1)'
        return None
    else:
        if max_order == 1:
            return np.arange(1, 11)
        elif max_order == 2:
            return np.arange(1, 101)
        else:
            first_two_orders = np.arange(1, 101)
            num_octaves = max_order - 2
            rest_of_orders = np.logspace(2, max_order, number_per_interval*num_octaves)
            return np.hstack((first_two_orders, rest_of_orders))

def get_simulation_df(sim, max_time_power = 8, run_sim=True):
    if run_sim:
        sim.run(10**max_time_power)

    # Let's make a pandas array of the results. It will be too annoying otherwise.
    wall_array = np.asarray(sim.num_walls_array)
    annih_array = np.asarray(sim.annihilation_array)
    coal_array = np.asarray(sim.coalescence_array)
    # Just make the time go from 0 to the max value to avoid problems.
    time_array = np.asarray(sim.time_array)

    df = pd.DataFrame(data={'wall_count': wall_array, 'annih': annih_array, 'coal':coal_array, 'time':time_array})

    return df

def average_simulations(sim, num_simulations = 100, **kwargs):
    '''Creates many simulations based off of sim and returns the combined dataframes.'''

    df_list = []
    for i in range(num_simulations):
        new_df = get_simulation_df(sim, **kwargs)
        new_df['sim_num'] = i
        df_list.append(new_df)
        new_seed = np.random.randint(0, 2**32 - 1)
        sim.reset(new_seed)
    return df_list

######## Averaging domain sizes from simulation ###############

def get_domain_size_df(completed_sim):
    angular_distances = []
    domain_types = []

    walls = np.asarray(completed_sim.wall_position_history)
    wall_types = np.asarray(completed_sim.wall_type_history)
    for count, cur_walls in enumerate(walls):
        cur_walls = np.array(cur_walls)
        angular_distances.append(cur_walls[1:] - cur_walls[0:-1])
        domain_types.append([wall_types[z][0] for z in range(1, len(wall_types))])

        if np.any(angular_distances[count] < 0):
            print 'Walls must not have been ordered correctly...'
            print count

    time_array = np.asarray(completed_sim.time_array)

    # Now wrap the data in a DF
    df_list = []
    for cur_ang, cur_type, time_point in zip(angular_distances, domain_types, time_array):
        df_list.append(pd.DataFrame({'angular_distance': cur_ang,
                                     'time':time_point,
                                    'type': cur_type}))

    df_combined = pd.concat(df_list)

    return df_combined


def get_average_domain_size_ecdf(completed_sim, num_ecdf_points=360):

    y_array = []
    time_array = []

    x = np.linspace(0, 2*np.pi, num_ecdf_points)

    walls = np.asarray(completed_sim.wall_position_history)
    angular_distances = []
    for count, cur_walls in enumerate(walls):
        cur_walls = np.array(cur_walls)
        angular_distances.append(cur_walls[1:] - cur_walls[0:-1])

        if np.any(angular_distances[count] < 0):
            print 'Walls must not have been ordered correctly...'
            print count

    sim_y = []
    for cur_angle in angular_distances:
        ecdf = sm.distributions.ECDF(cur_angle)
        y = ecdf(x)
        sim_y.append(y)
    y_array.append(sim_y)

    times = np.asarray(completed_sim.time_array)
    time_array.append(times)

    # Now wrap the data in a DF
    df_list = []
    for y_at_time_point, time_point in zip(y_array, time_array):
        df_list.append(pd.DataFrame({'angular_ecdf': y_at_time_point,
                                     'time':time_point,
                                    'angle':x}))

    df_combined = pd.concat(df_list)

    return df_combined

############### Matching with Experiment #########################

# These are the parameters when the random walk approximation begins to hold
INITIAL_RADIUS = 3.50
VELOCITY = 1.19
JUMP_LENGTH = .4
#LATTICE_SIZE = lambda q: 22/(1.-1./float(q))
SUPERDIFFUSIVE_JUMP_LENGTH = 0.1

def get_sim_experimental_match(num_colors, lattice_size, s=0.0, record_lattice=False, lattice_spacing_output=2*np.pi/500.,
                               max_power=1, record_every=None, verbose=False, superdiffusive=False):

    debug=False

    num_types = num_colors
    seed = np.random.randint(0, 2**32)
    record_wall_position = False

    #record_every=10.

    record_time_array = None
    if record_every is None:
        record_time_array = get_log_record_times(max_power).astype(np.double)

    # 1 will have the selective advantage, like our experiments
    delta_prob_dict = {}

    ##########################################################
    ##### These parameters should be checked & fine tuned! ###
    ##########################################################
    radius = INITIAL_RADIUS
    velocity= VELOCITY
    if not superdiffusive:
        jump_length= JUMP_LENGTH
    else:
        jump_length = SUPERDIFFUSIVE_JUMP_LENGTH

    # Selective disadvantage for one of them...strain 1, like in the experiments
    for i in range(num_types):
        for j in range(num_types):
            if i != j:
                if i == 1:
                    delta_prob_dict[i, j] = -s
                elif j == 1:
                    delta_prob_dict[i, j] = s
                else:
                    delta_prob_dict[i, j] = 0

    if record_every is None:
        sim = acwi.Selection_Inflation_Lattice_Simulation(
            delta_prob_dict,
            lattice_size = lattice_size,
            num_types = num_types,
            seed=seed,
            record_lattice=record_lattice,
            record_time_array=record_time_array,
            velocity=velocity,
            radius=radius,
            jump_length=jump_length,
            record_wall_position=record_wall_position,
            lattice_spacing_output=lattice_spacing_output,
            debug=debug,
            verbose=verbose, superdiffusive=superdiffusive)
    else:
        sim = acwi.Selection_Inflation_Lattice_Simulation(
            delta_prob_dict,
            lattice_size = lattice_size,
            num_types = num_types,
            seed=seed,
            record_lattice=record_lattice,
            record_every=record_every,
            velocity=velocity,
            radius=radius,
            jump_length=jump_length,
            record_wall_position=record_wall_position,
            lattice_spacing_output=lattice_spacing_output,
            debug=debug,
            verbose=verbose, superdiffusive=superdiffusive)

    return sim