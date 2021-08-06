import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import simpy
import random

# PRINTS AT START
st.title('Simulation tool for incoming deliveries')

st.write("Note, between arrival of a pallet and starting checks, every 20 pallets 30 minutes of waiting time occurs - on average. This also takes place between checking and labelling")
st.write("Follow this link to see the flow of the simulation: https://drive.google.com/file/d/1jDIaXIps10KcuU_oRdTScoSpBo9zc4DY/view?usp=sharing")
st.write("\n")
st.write("\n")

smoothing_factor = st.selectbox("Graphs can be smoothed to make them clearer, due to this, starting graphs seem to be incorrect. Upon creating a setup it will work correctly. Alter the smoothing factor using the slider below:", [1, 10, 20, 30, 40, 50])

red_line = st.selectbox("Y-axis position of red line")
yellow_line = st.selectbox("Y-axis position of yellow line")
# 

# INPUT VARIABLES
waiting_manpower = 9999999 # pseudo process which must always happen when called upon, so, unlimited capacity
checking_manpower = st.number_input('Number of employees working for: checking')
putaway_manpower = st.number_input('Number of employees working for: put away')


options_prob_full = []
for i in range(101):
    i = i / 100
    options_prob_full.append(i)
prob_full = st.sidebar.select_slider("Probability of a full pallet", options_prob_full)   # the probability of a full pallet inbound


fullpallets_checked_options = []
for i in range(100, 401):
    fullpallets_checked_options.append(i)
fullpallets_checked = st.sidebar.select_slider("Number of full pallets an employee can check per day", fullpallets_checked_options)


mixedpallets_checked_options = []
for i in range(1, 101):
    mixedpallets_checked_options.append(i)
mixedpallets_checked = st.sidebar.select_slider("Number of mixed pallets an employee can check per day", mixedpallets_checked_options)


pallets_labelled_options = []
for i in range(200, 1201):
    pallets_labelled_options.append(i)
pallets_labelled = st.sidebar.select_slider("Number of pallets an employee can label per day", pallets_labelled_options)


pallets_putaway_options = []
for i in range(50, 401):
    pallets_putaway_options.append(i)
pallets_putaway = st.sidebar.select_slider("Number of pallets an employee can put away per day", pallets_putaway_options)


duration = st.number_input("Duration of the simulation in days") # number of days to run the simulation for

pallets_per_day = st.number_input("Number of arriving pallets per day")





class InboundSimulator:
    
    def __init__(self):
        self.checking_duration = 0 # document the amount of time spent on checking
        self.putaway_duration = 0 # document theamount of time spent on putaway

        self.arrived_pallets = 0 # document the number of pallets arrived over time

        
        self.arrived_pallets_temp = 0 # document the number of pallets currently in temporary stock
        self.arrived_pallets_temp_list = [] # document the number of pallets currently in temporary stock
        self.unloaded_pallets = 0 # document the number of pallets currently unloaded but not yet checked
        self.unloaded_pallets_list = [] # document the number of pallets currently unloaded but not yet checked
        self.checked_pallets = 0 # document the number of pallets currently checked but not yet put away
        self.checked_pallets_list = [] # document the number of pallets currently checked but not yet put away

        self.checking_counter = 0 # document the number of pallets checked over time in total
        self.putaway_counter = 0 # document the number of pallets put away over time in total
           
        
    
    def InboundGenerator(self, env, waiting, checker, putaway):
        while True:
            pallet = self.pallet(env, waiting, checker, putaway) # generate a pallet

            
            env.process(pallet) # start simulation of an incoming pallet
            
            interarrival_time = random.expovariate(pallets_per_day) # the interarrival time is based on the earlier chosen number of pallets
            yield env.timeout(interarrival_time) # wait for sampled interarrival time
            
            self.arrived_pallets += 1 # 1 pallet arrives and is in temporary stock
            
            self.arrived_pallets_temp += 1 
            self.arrived_pallets_temp_list.append(self.arrived_pallets_temp) 
            
            self.unloaded_pallets += 1 # 1 pallet arrives and is in unloaded stock which is not yet checked
            self.unloaded_pallets_list.append(self.unloaded_pallets)

    def pallet(self, env, waiting, checker, putaway):
    # WAITING
    # with a probability of 0.05 there is a waiting time of 30 minutes, this simulates the fact that one can only start checking once the full truckload is unloaded
        temp = np.random.uniform(low=0, high=1)
        if temp > 0.95:
            waiting_request = waiting.request()
            yield waiting_request
            waiting_duration = random.expovariate(16)
            
            
    # CHECKING 
        
        checker_request = checker.request()
        yield checker_request
        start_checking = env.now

        
        checked_per_day_per_employee = fullpallets_checked # on average, one employee can check 200 full pallets per day
        
        temp = np.random.uniform(low=0, high=1)
        if temp > prob_full: # with a certain probability a mixed pallet arrives which takes extra time
            checked_per_day_per_employee = mixedpallets_checked # the mixed pallet takes the employee 15 minutes so he can only do 32 per day
         
        checking_duration = random.expovariate(checked_per_day_per_employee)
        yield env.timeout(checking_duration)
        end_checking = env.now 
        checker.release(checker_request)
        
    # WAITING
    # with a probability of 0.05 there is a waiting time of 30 minutes, this simulates the fact that one can only start stickering once the full truckload is checked
        temp = np.random.uniform(low=0, high=1)
        if temp > 0.95:
            waiting_request = waiting.request()
            yield waiting_request
            waiting_duration = random.expovariate(16)
    
    # STICKERING
    
        checker_request = checker.request()
        yield checker_request
        start_stickering = env.now
        
        stickering_duration = random.expovariate(pallets_labelled) # on average, one employee can sticker 480 full pallets per day
        yield env.timeout(stickering_duration)       
        end_stickering = env.now
        checker.release(checker_request)
        
        # document stock changes to keep up to date measurements
        self.checking_counter += 1
        self.checking_duration += checking_duration
        
        self.unloaded_pallets -= 1
        self.unloaded_pallets_list.append(self.unloaded_pallets)
        
        self.checked_pallets += 1
        self.checked_pallets_list.append(self.checked_pallets)

             
     # PUT AWAY
     
        putaway_request = putaway.request() 
        yield putaway_request     
        start_putaway = env.now 
        
        putaway_duration = random.expovariate(pallets_putaway) # on average, one employee can put away 232 pallets per day
        yield env.timeout(putaway_duration)
        end_putaway = env.now 
        putaway.release(putaway_request) 
        
        # document stock changes to keep up to date measurements
        self.putaway_counter += 1
        
        self.arrived_pallets_temp -= 1
        self.arrived_pallets_temp_list.append(self.arrived_pallets_temp)
        
        self.checked_pallets -= 1
        self.checked_pallets_list.append(self.checked_pallets)
        
        self.putaway_duration += putaway_duration



    def simulate(self):
        env = simpy.Environment() # set the environment
        
        checker = simpy.Resource(env, capacity = checking_manpower) # set the capacity of the number of available checkers
        putaway = simpy.Resource(env, capacity = putaway_manpower) # set the capacity of the number of available employees for put away
        waiting = simpy.Resource(env, capacity = waiting_manpower) # pseudo process so unlimited manpower
        
        env.process(self.InboundGenerator(env, waiting, checker, putaway)) # start the inbound generator which sends pallets
        
        env.run(duration) # run the simulation for XXXX days


# RUN SIMULATION            
sim = InboundSimulator()
sim.simulate()   



# smooth list based on number of steps (averaged over the number of steps specified)
def list_smoother(input_list):
    smoothed_list = []
    step = smoothing_factor + 1
    summer = 0
   
    for index, val in enumerate(input_list):
        if index % (step-1) != 0:
            summer += val
        else:
            summer += val
            avg = summer / step
            smoothed_list.append(avg)
            summer = 0

    return smoothed_list


fig, ax = plt.subplots()
ax.plot(list_smoother(sim.arrived_pallets_temp_list), )
plt.axhline(y = yellow_line, c='y')
plt.axhline(y = red_line, c='r')
plt.tick_params(left = True, right = False, labelleft = True, labelbottom = False, bottom = False)
ax.set_title("Temporary stock")
st.pyplot(fig)

fig, ax = plt.subplots(2)
fig.suptitle("Unloaded stock, not yet checked \n Checked and labelled stock, not yet put away")
plt.setp(plt.gcf().get_axes(), xticks=[])
ax[0].plot(list_smoother(sim.unloaded_pallets_list), )
ax[1].plot(list_smoother(sim.checked_pallets_list), )
plt.tick_params(left = True, right = False, labelleft = True, labelbottom = False, bottom = False)
st.pyplot(fig)


st.write("Over", duration, "days", sim.arrived_pallets, "pallets arrived, so on average", 
      round(sim.arrived_pallets / duration, 2), "pallets arrived per day","\n")

st.write("Checked and labelled pallets in total:", sim.checking_counter, "\n", 
      "Putawayed pallets in total:", sim.putaway_counter, "\n")




