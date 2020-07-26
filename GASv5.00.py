# created by svinec (2019) - use freely but please reference my original work, thanks :)

"""
SHORT INTRO

Operation scheduling is a classical problem in Operations Research. The problem arises when there are some number of operations that need to be
assigned to different resources for execution, and we don't know what the optimal way of assinging is.

Operations in this context can be anything from simple everyday tasks to complex manufacturing operations in a production facility.
Resources in this context is any entity or unit that can do work, for example a machine can be a resource, a human worker can be a resources,
or a whole team of people can be a resource - this is just an abstraction layer.
Optimal solution can have different meanings depending on the objective of the problem (i.e. it can be most constraints respected, least amount
of total time needed, etc.)

The scheduling problem easily becomes very complex when we have to respect different types of constraints and different given parameters of the
model. There are simply overwhelmingly too many possible ways of assigning a given set of operations to a given set of resources, so it is not
easy to tell which is the best or optimal way.

The complexity of this and other similar problems, means that there is no manageable mathematical formula or procedure that can be used to
reliably calculate an optimal solution to any given problem. People have tried various methods of tackling this problem, one of which is a Genetic
Algorithm. Generally speaking a GA is a form of a brute force search, i.e. it can search the whole space of solutions, but it won't do it one
by one. It will use the solutions it already has and take their good traits in order to predict the next better solution. It will keep doing so
until a good-enough solutuon is found. In doing so it mimicks the natural process of biological evolution, hence the name Genetic Algorithm.
Some more details can be found in this video https://www.youtube.com/watch?v=e84aLKGWtW4
"""

"""
CHANGE LOG

v5.00
- Tournament mode

v4.00
- reset function
- automated testing and dumping script
- average score calculation now caclulates average score within populations and then across populations (it used to take the best member of each population and then average it across populations)

v3.00
- two new complex examples
- printRandom and printAllScores
- mutation probability and mutation size
- average score calculation based on a sample of the latest populations
- specify crossMinStep
- specify crossMinStep and crossMaxStep in relative terms or absolute

v2.00 added features
- resource dependent operation duration and default duration for operation, plus scoring for fastest resources used
- can view separate scores for each scoring method
- improved performance - all scoring done in one iteration and not separate

v1.00 added features
- number of resources and resource succession weights
- operation time independent on resource
- operation relations with min and max offset and weights for each relation
- normal / asap / alap mode
- history keeping and retry count
- infuse random members to the population
- cross mode - max step
"""

import time, datetime
from random import randint
dtnow = datetime.datetime.now # a shortcut for logging messages


class GAS():
	""" This is the main class. It is self-sufficient, meaning that every instance of the class has its own set of parameters, operations, resource, etc.
	and can function on its own. Each instance of the class can capture only one problem and solve it."""

	def __init__( self, _parameters ):
		# When an instance is created, we take the input parameters and store them inside the instance. We also do some calculations (further below).
		self.resourceCount = int( _parameters[ "resourceCount" ] ) # The number of resources [1 <= integer < inf]
		self.populationSize = int( _parameters[ "populationSize" ] ) # The size of the population [1 <= integer < inf ] (a population is a collection of solutions, the number of solutions is the population size)
		self.population = [] # A container for the population [list of dictionaries {'start_times':[] , 'resources':[], 'score':int, 'genome':str}]
		self.survivalRate = float( _parameters[ "survivalRate" ] ) # What percent of the population survives on each breeding cycle [0.0 <= float <= 1.0]
		self.infuseRandomToPopulation = int( _parameters[ "infuseRandomToPopulation" ] ) # How many random solutions to add to the population on each breeding cycle [0 <= integer < inf]
		self.mutationProbability = float( _parameters[ "mutationProbability" ] ) # The probability of mutating the new genome after crossing the two genomes [0.0000 <= float <= 1.0000]. For example, a probability of 0.33 means that about one third of the new genomes generated on each breeding cycle will be mutated.
		self.mutationSize = float( _parameters[ "mutationSize" ] ) if type( _parameters[ "mutationSize" ] ) is float else int( _parameters[ "mutationSize" ] )
			# Mutation size controlls how many bits in the genome will have an attempted mutation. "Attempted" because there is a 50/50 chance to change from 0 to 1 or from 1 to 0.
			# If expressed as [0.0 <= float <= 1.0] then represents the relative size of the genome and an integer will be calculated later.
			# If expressed as [0 <= integer < inf] then it is the exact number of attempted mutations on bits from the genome.
		self.asapAlapMode = str( _parameters[ "asapAlapMode" ] )
			# Controlls how time constraints are scored [string]. Three modes are possible:
			# 'normal' - An operation relation will get a negative score only if the relation is outside of the Min and Max offsets defined for that relation
			# 'asap' - As soon as possible. Solutions that complete faster are scored higher.
			# 'alap' - As late as possible. Solutions that complete as late as possible are scored higher.
		self.weightResourceSuccession = int( _parameters[ "weightResourceSuccession" ] ) # Resource Succession means that each resource should be working on no more than one operation at any given time. Generated solutions might violate this constraint. If a constraint is violated then the solution is scored negatively with weightResourceSuccession [0 <= integer < inf]. It is a simple substraction from the total score therefore must be used wisely in conjunction with other scoring. For example, if you choose one unit of time to be one minute, and a solution violates an operation relation by 2 hours, e.g. 120, you might be okay with that if it's not critical, but if the Resource Succession is more critical for you then the weight should be something like 3000.
		self.historyKeep = bool( _parameters[ "historyKeep" ] ) # This option will force the algorithm to keep breeding new solutions until the new population has only unique solutions (the uniqueness is across all previous solutions) [boolean]. This can be incredibly slow and is generally discouraged. It's much better to cycle through a few repetitve solutions that to search a log of thousand previous solutions.
		self.historyRetryCount = int( _parameters[ "historyRetryCount" ] ) # Because finding a unique solution can sometime be very slow, this option tells the algoritm how many times to try before accepting a duplicate solution and adding to the new population [0 <= integer < inf]
		self.history = [] # A container for the history log [list of tuples (Start Times, Resources)]
		self.averageScoreSampleSize = int( _parameters[ "averageScoreSampleSize" ] ) # The average score is based on the best solutions from the last N generations [0 for disabled, else 1 <= integer < inf]. This can be a useful indicator if the solver is improving the solution over time or not.
		self.averageScoreSample = [] # A container for the best scores of the last N generations [list of integers]
		self.averageScore = None # The average score of the current solver
		self.tournamentPopulationSize = int( _parameters[ "tournamentPopulationSize" ] ) # When running in Tournament mode, this is the number of individuals to sample in total [1 <= integer < inf]
		self.tournamentPopulation = [] # A list that will hold the best individuals from each run
		self.tournamentSample = int( _parameters[ "tournamentSample" ] ) # The number of best individuals to collect from each run and save into the Tournamen population [1 <= integer < inf]
		self.tournamentGenerations = int( _parameters[ "tournamentGenerations" ] ) # The number of generations within each run of the solver before the best individuals are saved [1 <= integer < inf]
		
		self.operationDurations = {}
			# A definition of how much time each operation takes to complete. [dictionary] This is a unitless definition using integers. The meaning is assigned by the user, e.g. 1 can be one minute, one hour, one day, one 15-minute chunk, etc. Each operation duration can be defined in one of two different ways:
			# 1) If all resources take the same amount of time to complete the operation then [1 <= integer < inf]
			# 2) If different resources complete the operation in different amount of time then [list of integers, where the index matches the resource index]
		for i in _parameters[ "operationDurations" ]:
			if type( _parameters[ "operationDurations" ][ i ] ) is int:
				self.operationDurations[ i ] = int( _parameters[ "operationDurations" ][ i ] )
			elif type( _parameters[ "operationDurations" ][ i ] ) is list:
				self.operationDurations[ i ] = list( _parameters[ "operationDurations" ][ i ] ) # copy by value not by reference
			else:
				print( "{}\tInvalid operation duration: {}, type: {}\nTerminating".format( dtnow(), _parameters[ "operationDurations" ][ i ], type( _parameters[ "operationDurations" ][ i ] ) ) )
				return False
		
		self.operationCount = len( self.operationDurations ) # The number of operations [1 <= integer < inf]
		
		self.operationRelations = {}
			# A dictionary of two more nested dictionaries that stores operation relations. The structure is operationRelations[ op2 ][ op1 ][ parameter ], where:
			# 'op2' is the second operation in the relation
			# 'op1' is the first operation in the relation
			# 'parameter' can be either of four types of parameters:
			# 	- 'type' - available types or relations are:
			# 		- 'SS' - start-to-start - the start of the first operation relates to the start of the second operation
			# 		- 'SE' - start-to-end - the start of the first operation relates to the end of the second operation
			# 		- 'ES' - end-to-start - the end of the first operation relates to the start of the second operation
			# 		- 'EE' - end-to-end - the end of the first operation relates to the end of the second operation
			# 	- 'min' - the minimum time for the relation (for example, if the relation type is 'ES' and the min time is 10, it means that the second operation should start 10 units of time after the end of the first operation or later, but not sooner)
			# 	- 'max' - the maximum time for the relation (for example, if the relation type is 'ES' and the min time is 30, it means that the second operation should start 30 units of time after the end of the first operation or sooner, but not later)
			# 	- 'weight' - a custom weight used to fine-tune the scoring of schedules, default is 1
		
		for op2 in _parameters[ "operationRelations" ]: # copy by value not by reference
			self.operationRelations[ op2 ] = {}
			for op1 in _parameters[ "operationRelations" ][ op2 ]:
				self.operationRelations[ op2 ][ op1 ] = dict( _parameters[ "operationRelations" ][ op2 ][ op1 ] )
		
		# Evaluate the asapAlapMode
		for op2 in self.operationRelations:
			for op1 in self.operationRelations[ op2 ]:
				if self.asapAlapMode == "normal":
					if self.operationRelations[ op2 ][ op1 ][ "min" ] == None and self.operationRelations[ op2 ][ op1 ][ "max" ] == None:
						# If the mode is 'normal' and min and max are not specified, then we need at leas a min definition
						self.operationRelations[ op2 ][ op1 ][ "min" ] = 0
				elif self.asapAlapMode == "asap":
					if self.operationRelations[ op2 ][ op1 ][ "min" ] != None:
						# If the mode is 'asap' then we want to score solutions as if there is no later execution allowed
						self.operationRelations[ op2 ][ op1 ][ "max" ] = int( self.operationRelations[ op2 ][ op1 ][ "min" ] )
				elif self.asapAlapMode == "alap":
					if self.operationRelations[ op2 ][ op1 ][ "max" ] != None:
						# If the mode is 'alap' then we want to score solutions as if there is no early execution allowed
						self.operationRelations[ op2 ][ op1 ][ "min" ] = int( self.operationRelations[ op2 ][ op1 ][ "max" ] )
		
		self.operationMaxTime = 0 # The longest possible solution [1 <= integer < inf]. This is used later to find what the minimum lenght of the genome is in order to allow to represent all possible solutions
		for op in range( self.operationCount ): # It is a sum of all operation durations...
			if type( self.operationDurations[ op ] ) is int:
				self.operationMaxTime += self.operationDurations[ op ]
			else:
				self.operationMaxTime += max( self.operationDurations[ op ] )
		for op2 in self.operationRelations: # ...plus the sum of the largest relation offsets
			for op1 in self.operationRelations[ op2 ]:
				rel_min = self.operationRelations[ op2 ][ op1 ][ "min" ] if self.operationRelations[ op2 ][ op1 ][ "min" ] != None else 0
				rel_max = self.operationRelations[ op2 ][ op1 ][ "max" ] if self.operationRelations[ op2 ][ op1 ][ "max" ] != None else 0
				self.operationMaxTime += max( abs( rel_min ), abs( rel_max ) )
		
		# When two genomes are combined into a new one, this is done by splitting both genomes in steps. crossMinStep defines the minimum length of the step and crossMaxStep defines the maximum lenght of the step. crossMinStep must be less than or equal to crossMaxStep. They can be defined in one of two ways:
		# If expressed as [0.0 <= float <= 1.0] then it represents the size of the step relative to the genome length
		# If expressed as [0 <= integer < inf] then it is an exact number of characters (zeroes or ones)
		if type( _parameters[ "crossMinStep" ] ) is float:
			self.crossMinStep = int( round( ( self.operationMaxTime + self.resourceCount - 1 ) * self.operationCount * _parameters[ "crossMinStep" ] ) )
		else:
			self.crossMinStep = int( _parameters[ "crossMinStep" ] )
			
		if type( _parameters[ "crossMaxStep" ] ) is float:
			self.crossMaxStep = int( round( ( self.operationMaxTime + self.resourceCount - 1 ) * self.operationCount * _parameters[ "crossMaxStep" ] ) )
		else:
			self.crossMaxStep = int( _parameters[ "crossMaxStep" ] )
	
	# only reset runtime data so the model can be run again, but keep the parameters
	def reset( self ):
		self.population = []
		self.history = []
		self.averageScoreSample = []
		self.averageScore = None
		
	# for a given operation (and resource) return the duration of the operation
	def getOperationDuration( self, _op, _r = 0 ):
		if type( self.operationDurations[ _op ] ) is int:
			return int( self.operationDurations[ _op ] )
		elif type( self.operationDurations[ _op ] ) is list:
			return int( self.operationDurations[ _op ][ _r ] )
		else:
			print( "{}\tInvalid operation duration: {}, type: {}\nTerminating".format( dtnow(), _parameters[ "operationDurations" ][ i ], type( _parameters[ "operationDurations" ][ i ] ) ) )
			return False
	
	# add n number of random individuals to the population
	def addRandomToPopulation( self, _n ):
		for n in range( _n ):
			start_times = [ randint( 0, self.operationMaxTime ) for o in range( self.operationCount ) ]
			resources = [ randint( 0, self.resourceCount - 1 ) for o in range( self.operationCount ) ]
			
			if self.historyKeep == True:
				for i in range( self.historyRetryCount ):
					if ( start_times, resources ) not in self.history:
						self.history.append( ( list( start_times ), list( resources ) ) )
						break
					start_times = [ randint( 0, self.operationMaxTime ) for o in range( self.operationCount ) ]
					resources = [ randint( 0, self.resourceCount - 1 ) for o in range( self.operationCount ) ]
			
			self.population.append( { "start_times": list( start_times ), "resources": list( resources ), "score": 0, "genome": "" } )
			
		return True
	
	def scorePopulation( self ):
		for p in self.population: # for every member of the population do the below:
			p[ "score" ] = 0 # set the score to zero to clear previous scoring
			
			# Operation Relations - This section will score members based on whether the operation relations are violated or not
			# all operations are iterated... it looks a bit messy, but this it is actually well structured and this is what you get in order to check and score all different combinations
			for op2 in self.operationRelations: # as you can see here, it is important that the model is defined accurately otherwise can run into IndexErrors and KeyErrors
				start2 = p[ "start_times" ][ op2 ]
				end2 = p[ "start_times" ][ op2 ] + self.getOperationDuration( op2, p[ "resources" ][ op2 ] )
				
				for op1 in self.operationRelations[ op2 ]:
					start1 = p[ "start_times" ][ op1 ]
					end1 = p[ "start_times" ][ op1 ] + self.getOperationDuration( op1, p[ "resources" ][ op1 ] )
				
					if self.operationRelations[ op2 ][ op1 ][ "type" ] == "SS":
					
						if self.operationRelations[ op2 ][ op1 ][ "min" ] != None:
							threshold_min = start2 - ( start1 + self.operationRelations[ op2 ][ op1 ][ "min" ] )
							if threshold_min < 0: p[ "score" ] += threshold_min * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "asap":
							p[ "score" ] -= start2
							
						if self.operationRelations[ op2 ][ op1 ][ "max" ] != None:
							threshold_max = ( start1 + self.operationRelations[ op2 ][ op1 ][ "max" ] ) - start2
							if threshold_max < 0: p[ "score" ] += threshold_max * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "alap":
							p[ "score" ] += start2
							
					elif self.operationRelations[ op2 ][ op1 ][ "type" ] == "SE":
					
						if self.operationRelations[ op2 ][ op1 ][ "min" ] != None:
							threshold_min = end2 - ( start1 + self.operationRelations[ op2 ][ op1 ][ "min" ] )
							if threshold_min < 0: p[ "score" ] += threshold_min * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "asap":
							p[ "score" ] -= start2
							
						if self.operationRelations[ op2 ][ op1 ][ "max" ] != None:
							threshold_max = ( start1 + self.operationRelations[ op2 ][ op1 ][ "max" ] ) - end2
							if threshold_max < 0: p[ "score" ] += threshold_max * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "alap":
							p[ "score" ] += start2
							
					elif self.operationRelations[ op2 ][ op1 ][ "type" ] == "ES": # if the relation between op1 and op2 is End-to-Start, meaning op2 cannot start until op1 has ended (one of the most common type of relations):
					
						if self.operationRelations[ op2 ][ op1 ][ "min" ] != None: # (a) If there is a min offset specified then we take it into account by adjusting the score...
							threshold_min = start2 - ( end1 + self.operationRelations[ op2 ][ op1 ][ "min" ] ) # (b) The start of op2 should be greater than the end of op1 plus the min offset...
							if threshold_min < 0: p[ "score" ] += threshold_min * self.operationRelations[ op2 ][ op1 ][ "weight" ] # (b) ... otherwise, subtract (it is already negative) the difference from the score adjusted by the specific weight for this relation. In this way the smaller the violation of the min offset, the better the score.
						elif self.asapAlapMode == "asap": # (a) ... Otherwise, check if the mode is 'asap'. This is mutually exclusive with a min offset that's why it is in an 'elif' statement. In this case subtract the start time of op2 from the score - the sooner all operations start the better the score will be.
							p[ "score" ] -= start2
							
						if self.operationRelations[ op2 ][ op1 ][ "max" ] != None: # (c) If there is a max offset specified then we take it into account by adjusting the score...
							threshold_max = ( end1 + self.operationRelations[ op2 ][ op1 ][ "max" ] ) - start2 # (d) The start of op2 should be no greater than the end of op1 plus the max offset...
							if threshold_max < 0: p[ "score" ] += threshold_max * self.operationRelations[ op2 ][ op1 ][ "weight" ] # (d) ... otherwise, subtract (it is already negative) the difference from the score adjusted by the specific weight for this relation. In this way the smaller the violation of the max offset, the better the score.
						elif self.asapAlapMode == "alap": # (c) ... Otherwise, check if the mode is 'alap'. This is mutually exclusive with a max offset that's why it is in an 'elif' statement. In this case add the start time of op2 to the score - the later all operations start the better the score will be.
							p[ "score" ] += start2
							
					elif self.operationRelations[ op2 ][ op1 ][ "type" ] == "EE":
					
						if self.operationRelations[ op2 ][ op1 ][ "min" ] != None:
							threshold_min = end2 - ( end1 + self.operationRelations[ op2 ][ op1 ][ "min" ] )
							if threshold_min < 0: p[ "score" ] += threshold_min * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "asap":
							p[ "score" ] -= start2
							
						if self.operationRelations[ op2 ][ op1 ][ "max" ] != None:
							threshold_max = ( end1 + self.operationRelations[ op2 ][ op1 ][ "max" ] ) - end2
							if threshold_max < 0: p[ "score" ] += threshold_max * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "alap":
							p[ "score" ] += start2
					else:
						print( "{}\tInvalid relation type {} at self.operationRelations[ {} ][ {} ][ 'type' ]".format( dtnow(), self.operationRelations[ op2 ][ op1 ][ "type" ], op2, op1 ) )
						return False
			
			p[ "score_operationRelations" ] = int( p[ "score" ] ) # 'score' is the main score used, 'score_operationRelations' is just to store this score separately
			
			
			# Resource Succession - This section will score members based on whether resources have been assigned one operation at a time or not
			p[ "score_resourceSuccession" ] = int( p[ "score" ] )
			
			sorted_operations = [] # build a list of all operations and resources which will be sorted, the list is composed of tuples: ( operations id, start time, resource id )
			for i in range( self.operationCount ):
				sorted_operations.append( ( i, int( p[ "start_times" ][ i ] ), int( p[ "resources" ][ i ] ) ) )
			sorted_operations.sort( key = lambda x: ( x[ 2 ], x[ 1 ] ) ) # first sort by resource id, then by operation start time
			
			for i in range( 1, self.operationCount ): # iterate from the second operation to the end
				op1 = sorted_operations[ i-1 ][ 0 ]
				op2 = sorted_operations[ i ][ 0 ]
				r1 = sorted_operations[ i-1 ][ 2 ]
				r2 = sorted_operations[ i ][ 2 ]
				
				if r1 == r2: # if the resource id is the same between two entries then we need to check if there is overlap of operations on that resource
					# we do this by checking if one operation starts before the other one has finished
					if p[ "start_times" ][ op2 ] < p[ "start_times" ][ op1 ] + self.getOperationDuration( op1, p[ "resources" ][ op1 ] ):
						p[ "score" ] -= self.weightResourceSuccession # and if yes, reduce the total score by weightResourceSuccession
			
			p[ "score_resourceSuccession" ] = int( p[ "score" ] - p[ "score_resourceSuccession" ] ) # 'score' is the main score used, 'score_resourceSuccession' is just to store this score separately
			
			
			# Fastest Resource - This section will score members based on whether operations are being assigned to the resources that will execute them the fastest
			p[ "score_fastestResource" ] = int( p[ "score" ] )
			
			for op in range( self.operationCount ):
				# It simply means subtracting the operation duration of the currently assigned resource from the total score. Thus, schedules where fastest resources are used will have higher scores overall.
				p[ "score" ] -= self.getOperationDuration( op, p[ "resources" ][ op ] )
			
			p[ "score_fastestResource" ] = int( p[ "score" ] - p[ "score_fastestResource" ] ) # 'score' is the main score used, 'score_fastestResource' is just to store this score separately
			
		return True
	
	# for every member of the population, calculate a genome by taking start times and resource ids and convering to a string of zeroes and ones
	def calculatePopulationGenome( self ):
		resourceCount = self.resourceCount - 1 if self.resourceCount > 1 else 1
		
		for p in self.population:
			p[ "genome" ] = "" # first, clear existing genome
			for i in range( self.operationCount ): # then, for every operation in the model convert start time and resource id to string and append to the genome in the same order
				p[ "genome" ] += self.numberToString( p[ "start_times" ][ i ], self.operationMaxTime )
				p[ "genome" ] += self.numberToString( p[ "resources" ][ i ], resourceCount )
		return True
	
	# A generic function handles both start time and resource id conversion. This is possible because numbers are encoded as the number of 1s in a string, thus 0010111011 is the number 6 because there are six ones
	def numberToString( self, _number, _length ): # the functions needs to know the number and the maximum number possible, which is eiher operationMaxTime or resourceCount
		number = int( _number ) # the number itself, or also the number of ones
		padding = int( _length - _number ) # padding is the number of zeroes
		probability = int( round( 100 * ( padding / _length ) ) ) # We want to space out ones and zeroes evenly and we can do this using a probability. For example, we don't want to have 1111110000, instead we want something like 0010111011
		string = ""
		while number + padding > 0: # the loop works by consuming the number and the padding, once these are consumed our job is done and the loop stops
			if number == 0: # if have no more 1s left to assign, then we assign a 0...
				string += "0"
				padding -= 1
				continue # ... and continue because there might be more 0s to assign
			if padding == 0: # if have no more 0s left to assign, then we assign a 1...
				string += "1"
				number -= 1
				continue # ... and continue because there might be more 1s to assign
			if randint( 0, 100 ) < probability: # otherwise, there are still both 1s and 0s to assign, so the probability helps us pick which one to assign next in order to space them evenly
				string += "0"
				padding -= 1
			else:
				string += "1"
				number -= 1
		return string
		
	# This is the heart of everything. When this method is called it drives all the logic and processing. One call of the method is equal to one cycle of evolutiom, meaning we start with one population and end up with a different one which s derived from the first one. Needless to say, the order of actions below matters.
	def breedPopulation( self, do_print = False, print_text = "" ):
		self.scorePopulation() # first, whatever population we have, we want to score it
		self.population.sort( key = lambda x: x[ "score" ], reverse = True ) # then sort it by descending score, meaning highest score first
		
		if do_print: self.printBestNormalized( print_text )
		
		# this is where we capture information about the average score calculation
		if self.averageScoreSampleSize > 0:
			average = sum( [ p[ "score" ] for p in self.population ] ) # calculate the average score for the whole population
			average = int( average / self.populationSize )
			self.averageScoreSample.append( average ) # append it to the list that tracks average score across populations
			if len( self.averageScoreSample ) > self.averageScoreSampleSize: # if we have more samples than what is defined...
				del self.averageScoreSample[ 0 ] # ... remove the earliest one and leave the rest
				self.averageScore = sum( self.averageScoreSample ) / self.averageScoreSampleSize # calculate the average score across populations and save it as current - this can later be printed
		
		# we are now in a position where we can discard members from the current population
		survivors = int( round( self.survivalRate * self.populationSize ) ) # the number of members to keep / survive
		for i in range( survivors, self.populationSize ): # the rest are deleted
			del self.population[ -1 ] # [-1] means last element and since this is sorted by descending score, we are laywas discarding the worst members
		
		# now is the time to add random members to the population if the model specifies so
		if self.infuseRandomToPopulation > 0:
			self.addRandomToPopulation( self.infuseRandomToPopulation )
			#self.calculatePopulationGenome()
			self.scorePopulation()
		
		# create genomes for all members of the current population so we can start breeding the population
		self.calculatePopulationGenome()
		
		new_population = [] # first we build the new population and then we assign it to the model
		for n in range( self.populationSize ): # we generate the same number of members for the new population
			p1 = randint( 0, len( self.population ) - 1 ) # pick two random members from the current population
			p2 = randint( 0, len( self.population ) - 1 )
		
			genome1 = str( self.population[ p1 ][ "genome" ] ) # take their genomes
			genome2 = str( self.population[ p2 ][ "genome" ] )
			
			new_genome = str( self.crossTwoGenomes( genome1, genome2 ) ) # and combine them into a new genome
			start_times, resources = self.genomeToValues( new_genome ) # then convert the new genome back to start times and resource ids
			
			if self.historyKeep == True: # if history tracking is switched on, we need to save the new members to the history log
				for i in range( self.historyRetryCount ): # 
					if ( start_times, resources ) not in self.history: # if the new member is not in the history log, then add it, otherwise keep trying to generate a new member until a unique one is found or until the maximum number of tries is exhausted
						self.history.append( ( list( start_times ), list( resources ) ) )
						break
					genome1 = str( self.population[ randint( 0, len( self.population ) - 1 ) ][ "genome" ] )
					genome2 = str( self.population[ randint( 0, len( self.population ) - 1 ) ][ "genome" ] )
					new_genome = str( self.crossTwoGenomes( genome1, genome2 ) )
					start_times, resources = self.genomeToValues( new_genome )
			
			# add the new member to the new population
			new_population.append( { "start_times": list( start_times ), "resources": list( resources ), "score": 0, "genome": str( new_genome ) } )
		
		self.population.clear() # clear the existing population
		self.population = list( new_population ) # and assign the new population
		
		return True
	
	# take two genomes, combine them randomly and return a new one
	def crossTwoGenomes( self, _genome1, _genome2 ):
		genome_length = len( _genome1 )
		index = 0
		result_genome = "";
		
		while True:
			step = randint( self.crossMinStep, self.crossMaxStep ) # each time define a new random step between the min and max limit
			if step > genome_length - ( index + 1 ): # if the step goes beyond the end of the genome, then we only need to take what's left from the genome
				if randint( 0, 99 ) < 50: # randomly choose which genome to copy data from
					result_genome += _genome1[ index : ]
				else:
					result_genome += _genome2[ index : ]
				break
			if randint( 0, 99 ) < 50: # otherwise, the step is short from the end of the genome so take the step and again randomly choose which genome to copy data from
				result_genome += _genome1[ index : index + step ]
			else:
				result_genome += _genome2[ index : index + step ]
			index += step
		
		if self.mutationProbability > 0: # here we also implement the mutation feature
			if randint( 1, 10000 ) < self.mutationProbability * 10000:
				result_genome = list( result_genome ) # convert the string to a list so we can access and change individual letters
				
				if type( self.mutationSize ) is float:
					number_of_mutations = int( round( len( result_genome ) * self.mutationSize ) ) # if the parameter is float then it represents relative size of the genome and find what number that translates to
				else:
					number_of_mutations = int( self.mutationSize ) # else, we take the value, not the reference
					
				for i in range( number_of_mutations ):
					p = randint( 0, len( result_genome ) - 1 )
					result_genome[ p ] = "0" if randint( 0, 99 ) < 50 else "1" # randomize that many random bits in the genome
					
				result_genome = "".join( result_genome ) # and convert back to a single string
		
		return result_genome
	
	# This function is the opposite of numberToString. It takes a genome as an input and converts it to start times and resource ids
	def genomeToValues( self, _genome ):
		start_times = []
		resources = []
		segment = self.operationMaxTime + ( self.resourceCount - 1 if self.resourceCount > 1 else 1 ) # A segment contains the number of bits needed to represent one operation - the highest possible start time plus the highest possible resource ids.
		
		for i in range( self.operationCount ): # The number of segments in a genome is equal to the number of operations.
			st_from = i * segment # the beginning of the start time string
			st_to = i * segment + self.operationMaxTime # the end of the start time string
			r_from = i * segment + self.operationMaxTime # the beginning of the resource id string
			r_to = ( i + 1 ) * segment # the end of the resource id string
			
			start_times.append( _genome[ st_from : st_to ].count( "1" ) ) # as previously mentioned, numbers are encoded as the number of ocurrences of 1s
			resources.append( _genome[ r_from : r_to ].count( "1" ) )
			
		return start_times, resources
		
	""" Beginning with version 5.00, Tournament is a new mode that accumulates best individuals from each run until a new population is formed, called the Tournament population.
	The new population then becomes the starting point of a run of the solver and continues indefinitely.
	The run can be interrupted with Ctrl+C which will prompt for a value:
		- Providing no value and hiting enter will start a new run with the same Tournament population.
		- Providing any other value will exit the script. Also, doing Ctrl+C during the prompt will exit the script.
	"""
	def tournament( self ):
		keepbreeding = True
		while keepbreeding: # keep looping until the Tournament population has been filled with individuals; each cycle of the loop is refer to as "run of the solver" or "run of the model"
			self.reset()
			self.addRandomToPopulation( self.populationSize ) # every run starts with a random population
			for g in range( self.tournamentGenerations ): 
				self.breedPopulation( do_print=True, print_text="TrnmPop{}of{}".format( len( self.tournamentPopulation ), self.tournamentPopulationSize ) )
			for i in range( self.tournamentSample ): # how many best individuals to take from the current population...
				self.tournamentPopulation.append( self.getIndividualAsACopy( self.population, i ) ) # ...and add to the Tournament population
				if len( self.tournamentPopulation ) == self.tournamentPopulationSize:
					keepbreeding = False # make sure the parent loop will break, too
					break
					
		while True: # now that we have a Tournament population, we start breeding the population
			try:
				self.reset()
				self.populationSize = self.tournamentPopulationSize
				self.population = [ self.getIndividualAsACopy( self.tournamentPopulation, i ) for i in range( self.tournamentPopulationSize ) ] # the Tournament population is not consumed, but copied, so can be resued
				while True: # the breeding will continue indefinitely...
					self.breedPopulation( do_print=True, print_text="Trnmnt" )
			except KeyboardInterrupt: # ...until you press Ctrl+C...
				reply = input( "Press Enter to start a new run with the tournament population..." )
				if reply != "": # ...and here you have a choice to start again with the same Tournament population or exit the script
					break
					
	def getIndividualAsACopy( self, source, i ):
		return_dict = {}
		return_dict[ "start_times" ] = list( source[ i ][ "start_times" ] )
		return_dict[ "resources" ] = list( source[ i ][ "resources" ] )
		return_dict[ "score" ] = int( source[ i ][ "score" ] )
		return_dict[ "genome" ] = str( source[ i ][ "genome" ] )
		return return_dict
		
	# A function that prints the current state of the model. 'Normalized' means to shift the whole schedule earlier so it begins at time 0. For example, a start times [ 3, 7, 2, 10 ] is normalized to [ 1, 5, 0, 8 ] because in essence it is the same schedule.
	def printBestNormalized( self, _text = '' ):
		min_start_time = min( self.population[ 0 ][ "start_times" ] ) # find the lowest start time...
		start_times = []
		for i in self.population[ 0 ][ "start_times" ]:
			start_times.append( i - min_start_time ) # ... and subtract it from every start time
		# then print some information
		print( "{} avg: {}, score: {}, s_opRel: {}, s_resSucc: {}, s_fastRes: {}".format(
				_text,
				round( self.averageScore, 1 ) if self.averageScore else self.averageScore,
				self.population[ 0 ][ "score" ],
				self.population[ 0 ][ "score_operationRelations" ],
				self.population[ 0 ][ "score_resourceSuccession" ],
				self.population[ 0 ][ "score_fastestResource" ],
				#start_times
				#self.population[ 0 ][ "resources" ]
			)
		)

	# prints a random member of the current population
	def printRandom( self, _text = '' ):
		i = randint( 0, len( self.population ) - 1 )
		print( _text + " avg: {}\tscore: {}\ts_opRel: {}\ts_resSucc: {}\ts_fastRes: {}\tstart_times: {}\tresources: {}".format(
				self.averageScore,
				self.population[ i ][ "score" ],
				self.population[ i ][ "score_operationRelations" ],
				self.population[ i ][ "score_resourceSuccession" ],
				self.population[ i ][ "score_fastestResource" ],
				self.population[ i ][ "start_times" ],
				self.population[ i ][ "resources" ]
			)
		)
	
	# print all scores from the current population in descending order
	def printAllScores( self, _text = '' ):
		all_scores = [ p[ "score" ] for p in self.population ]
		all_scores.sort( reverse = True )
		print( _text + " " + str( all_scores ) )
	
	# This is a function that automates the testing of the model. The same problem definition can be solved using several different combinations of parameters in order to find out which combination works best. Then you can use the best combination to do some more solving and hopefully find an even better solution.
	# For example, it can help you answer questions such as: Is it better to have many generations with a small population size or rather have fewer generations with a large population size, or does it not matter overall?
	def automatedTest( self ):
		# Below are the input parameters to the function. Change these to suit your needs.
		# ****************************************
		filename = "automatedTest_results.txt" # the file which to write the results to
		at_generations = [ 50, 150, 300 ] # the number of generations (or cycles) in each run, i.e. how many times the population will breed and create new solutions
		at_runs = [ 5 ] # the number of runs to carry out for each combination of parameters; remember that on each new run the population is totally randomizd initially
		at_cross_min_step = [ 0.05, 0.15, 0.35 ]
		at_cross_max_step = [ 0.1, 0.3, 0.5 ]
		at_population_size = [ 50, 200, 600 ]
		at_survival_rate = [ 0.05, 0.15, 0.5 ]
		at_mutate_prob = [ 0, 0.05, 0.15, 0.5 ]
		at_mutate_size = [ 0.05, 0.15, 0.25 ]
		at_infuse_random = [ 0, 5, 15, 30 ]
		# ****************************************
		
		number_of_combinations = len( at_generations ) * len( at_cross_min_step ) * len( at_cross_max_step ) * len( at_population_size ) * len( at_survival_rate ) * len( at_mutate_prob ) * len( at_mutate_size ) * len( at_infuse_random )
		current_combination = 0
		
		line_template = "{}\t" * 25 + "\n"
		with open( filename, "at", encoding = "utf-8" ) as f:
			f.write( line_template.format(
				"Combination #",
				"Run #",
				"Time",
				
				"Best Score",
				"Average Score",
				"Worst Score",
				
				"Operation Relations score - Best",
				"Operation Relations score - Average",
				"Operation Relations score - Worst",
				
				"Resource Succession score - Best",
				"Resource Succession score - Average",
				"Resource Succession score - Worst",
				
				"Fastest Resource score - Best",
				"Fastest Resource score - Average",
				"Fastest Resource score - Worst",
				
				"Generations",
				"Cross Min Step",
				"Cross Max Step",
				"Population Size",
				"Survival Rate",
				"Mutation Probability",
				"Mutation Size",
				"Infuse Random",

				"Best Solution Start Times",
				"Best Solution Resource IDs"
				) )
		
		for cross_min in at_cross_min_step:
			for cross_max in at_cross_max_step:
				if cross_min > cross_max:
					# if Cross Min Step is greater than Cross Max Step then skip all these combinations and continue to next step values
					current_combination += len( at_generations ) * len( at_population_size ) * len( at_survival_rate ) * len( at_mutate_prob ) * len( at_mutate_size ) * len( at_infuse_random )
					continue
					
				for pop_size in at_population_size:
					for sur_rate in at_survival_rate:
						for mut_prob in at_mutate_prob:
							for mut_size in at_mutate_size:
								for inf_rand in at_infuse_random:
									
									if type( cross_min ) is float: self.crossMinStep = int( round( ( self.operationMaxTime + self.resourceCount - 1 ) * self.operationCount * cross_min ) )
									else: self.crossMinStep = int( cross_min )
									if type( cross_max ) is float: self.crossMaxStep = int( round( ( self.operationMaxTime + self.resourceCount - 1 ) * self.operationCount * cross_max ) )
									else: self.crossMaxStep = int( cross_max )
									
									self.populationSize = int( pop_size )
									self.survivalRate = float( sur_rate )
									self.mutationProbability = float( mut_prob )
									self.mutationSize = float( mut_size ) if type( mut_size ) is float else int( mut_size )
									self.infuseRandomToPopulation = int( inf_rand )
									
									for gen in at_generations:
										current_combination += 1
										for runs in at_runs:
											for r in range( runs ):
											
												print( "{}\tRunning combination {} of {}, run number {} of {}".format( dtnow(), current_combination, number_of_combinations, r+1, runs ) )
												# just before running reset and initialize the model
												self.reset()
												self.addRandomToPopulation( self.populationSize )
												
												time_start = time.time()
												for g in range( gen ):
													self.breedPopulation()
												time_end = time.time()
												
												self.scorePopulation()
												self.population.sort( key = lambda x: x[ "score" ], reverse = True )
												
												score_operationRelations = tuple( p[ "score_operationRelations" ] for p in self.population )
												score_resourceSuccession = tuple( p[ "score_resourceSuccession" ] for p in self.population )
												score_fastestResource = tuple( p[ "score_fastestResource" ] for p in self.population )
												
												output_line = line_template.format(
													current_combination,
													r+1,
													round( time_end - time_start, 2 ),
													
													self.population[ 0 ][ "score" ],
													self.averageScore,
													self.population[ -1 ][ "score" ],
													
													max( score_operationRelations ),
													sum( score_operationRelations ) / len( score_operationRelations ),
													min( score_operationRelations ),
													
													max( score_resourceSuccession ),
													sum( score_resourceSuccession ) / len( score_resourceSuccession ),
													min( score_resourceSuccession ),
													
													max( score_fastestResource ),
													sum( score_fastestResource ) / len( score_fastestResource ),
													min( score_fastestResource ),
													
													gen,
													cross_min,
													cross_max,
													pop_size,
													sur_rate,
													mut_prob,
													mut_size,
													inf_rand,
													
													self.population[ 0 ][ "start_times" ],
													self.population[ 0 ][ "resources" ]
												)
												
												with open( filename, "at", encoding = "utf-8" ) as f:
													f.write( output_line )



# ideal solution
# start_times = [ 0, 4, 8, 12, 16 ]
# resources = [ 0, 1, 0, 1, 0 ]
operation_durations_simple_1 = {
	0: [ 4, 10 ],
	1: [ 10, 4 ],
	2: [ 4, 10 ],
	3: [ 10, 4 ],
	4: [ 4, 10 ]
}
operation_relations_simple_1 = {
	1: {
		0: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	2: {
		1: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	3: {
		2: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	4: {
		3: { "type":"ES", "min":0, "max":0, "weight":1 }
	}
}



# ideal solution?
# start_times = [ 5, 6, 17, 0, 14 ]
# resources = [ 0, 1, 0, 1, 1 ]
operation_durations_simple_2 = {
	0: [ 7, 5 ],
	1: [ 7, 5 ],
	2: [ 7, 5 ],
	3: [ 7, 5 ],
	4: [ 7, 5 ]
}
operation_relations_simple_2 = {
	0: {
		3: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	4: {
		0: { "type":"ES", "min":2, "max":2, "weight":1 },
		1: { "type":"EE", "min":8, "max":8, "weight":1 }
	},
	2: {
		1: { "type":"SS", "min":11, "max":11, "weight":1 }
	}
}



# ideal solution
# start_times = [ 0, 4, 4, 8, 12, 16, 20, 20, 24, 28, 32, 32, 36, 40, 44, 48, 52, 52, 56, 60 ]
# resources = [ 0, 1, 2, 0, 2, 1, 0, 2, 1, 2, 0, 1, 2, 0, 2, 1, 0, 2, 1, 0 ]
operation_durations_complex_1 = {
	0: [ 4, 10, 10 ],
	1: [ 10, 4, 10 ],
	2: [ 10, 10, 4 ],
	3: [ 4, 10, 10 ],
	4: [ 10, 10, 4 ],
	5: [ 10, 4, 10 ],
	6: [ 4, 10, 10 ],
	7: [ 10, 10, 4 ],
	8: [ 10, 4, 10 ],
	9: [ 10, 10, 4 ],
	10: [ 4, 10, 10 ],
	11: [ 10, 4, 10 ],
	12: [ 10, 10, 4 ],
	13: [ 4, 10, 10 ],
	14: [ 10, 10, 4 ],
	15: [ 10, 4, 10 ],
	16: [ 4, 10, 10 ],
	17: [ 10, 10, 4 ],
	18: [ 10, 4, 10 ],
	19: [ 4, 10, 10 ],
}
operation_relations_complex_1 = {
	1: {
		0: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	2: {
		0: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	3: {
		1: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	3: {
		2: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	4: {
		3: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	5: {
		4: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	6: {
		5: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	7: {
		5: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	8: {
		6: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	8: {
		7: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	9: {
		8: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	10: {
		9: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	11: {
		9: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	12: {
		10: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	12: {
		11: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	13: {
		12: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	14: {
		13: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	15: {
		14: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	16: {
		15: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	17: {
		15: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	18: {
		16: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	18: {
		17: { "type":"ES", "min":0, "max":0, "weight":1 }
	},
	19: {
		18: { "type":"ES", "min":0, "max":0, "weight":1 }
	}
}



# ideal solution
# start_times = [ 24, 35, 34, 32, 22, 13, 24, 3, 7, 10, 0 ]
# resources = [ 1, 2, 0, 1, 2, 0, 0, 1, 2, 1, 0 ]
operation_durations_complex_2 = {
	0: [ 7, 6, 7 ],
	1: [ 12, 12, 8 ],
	2: [ 5, 8, 6 ],
	3: [ 7, 3, 5 ],
	4: [ 13, 8, 5 ],
	5: [ 7, 9, 10 ],
	6: [ 6, 10, 10 ],
	7: [ 7, 4, 6 ],
	8: [ 14, 10, 8 ],
	9: [ 7, 5, 6 ],
	10: [ 10, 12, 14 ]
}
operation_relations_complex_2 = {
	7: {
		10: { "type":"ES", "min":-7, "max":-7, "weight":1 }
	},
	9: {
		7: { "type":"ES", "min":3, "max":3, "weight":1 },
		10: { "type":"EE", "min":5, "max":5, "weight":1 }
	},
	8: {
		9: { "type":"SS", "min":-3, "max":-3, "weight":1 }
	},
	6: {
		8: { "type":"EE", "min":15, "max":15, "weight":1 }
	},
	5: {
		6: { "type":"SE", "min":-4, "max":-4, "weight":1 }
	},
	4: {
		5: { "type":"SS", "min":9, "max":9, "weight":1 }
	},
	0: {
		4: { "type":"EE", "min":3, "max":3, "weight":1 }
	},
	2: {
		0: { "type":"SE", "min":15, "max":15, "weight":1 }
	},
	3: {
		2: { "type":"EE", "min":-4, "max":-4, "weight":1 }
	},
	1: {
		3: { "type":"SS", "min":3, "max":3, "weight":1 }
	}
}



parameters_simple_1 = {
	"resourceCount": 2,
	"populationSize": 100,
	"survivalRate": 0.2,
	"infuseRandomToPopulation": 0,
	"crossMinStep": 0.1,
	"crossMaxStep": 0.18,
	"mutationProbability": 0.1,
	"mutationSize": 0.1,
	"asapAlapMode": "normal",
	"weightResourceSuccession": 5,
	"historyKeep": False,
	"historyRetryCount": 0,
	"averageScoreSampleSize": 10,
	"operationDurations": operation_durations_simple_1,
	"operationRelations": operation_relations_simple_1
}

parameters_simple_2 = {
	"resourceCount": 2,
	"populationSize": 100,
	"survivalRate": 0.2,
	"infuseRandomToPopulation": 0,
	"crossMinStep": 0.1,
	"crossMaxStep": 0.18,
	"mutationProbability": 0.1,
	"mutationSize": 0.1,
	"asapAlapMode": "normal",
	"weightResourceSuccession": 5,
	"historyKeep": False,
	"historyRetryCount": 0,
	"averageScoreSampleSize": 10,
	"operationDurations": operation_durations_simple_2,
	"operationRelations": operation_relations_simple_2
}

parameters_complex_1 = {
	"resourceCount": 3,
	"populationSize": 300,
	"survivalRate": 0.15,
	"infuseRandomToPopulation": 0,
	"crossMinStep": 0.1,
	"crossMaxStep": 0.15,
	"mutationProbability": 0.1,
	"mutationSize": 0.05,
	"asapAlapMode": "normal",
	"weightResourceSuccession": 5,
	"historyKeep": False,
	"historyRetryCount": 0,
	"averageScoreSampleSize": 70,
	"operationDurations": operation_durations_complex_1,
	"operationRelations": operation_relations_complex_1
}

parameters_complex_2 = {
	"resourceCount": 3,
	"populationSize": 300,
	"survivalRate": 0.15,
	"infuseRandomToPopulation": 0,
	"crossMinStep": 0.1,
	"crossMaxStep": 0.15,
	"mutationProbability": 0.1,
	"mutationSize": 0.05,
	"asapAlapMode": "normal",
	"weightResourceSuccession": 5,
	"historyKeep": False,
	"historyRetryCount": 0,
	"averageScoreSampleSize": 70,
	"operationDurations": operation_durations_complex_2,
	"operationRelations": operation_relations_complex_2
}



parameters_testing = {
	"resourceCount": 3,
	"populationSize": 600,
	"survivalRate": 0.18,
	"infuseRandomToPopulation": 1,
	"crossMinStep": 0.1,
	"crossMaxStep": 0.4,
	"mutationProbability": 0.1,
	"mutationSize": 0.12,
	"asapAlapMode": "normal",
	"weightResourceSuccession": 5,
	"historyKeep": False,
	"historyRetryCount": 0,
	"averageScoreSampleSize": 70,
	"tournamentPopulationSize": 100,
	"tournamentSample": 10,
	"tournamentGenerations": 70,
	"operationDurations": operation_durations_complex_1,
	"operationRelations": operation_relations_complex_1
}



# in order to test in real time, do something like:
GAS_testing = GAS( parameters_testing )
GAS_testing.addRandomToPopulation( GAS_testing.populationSize )
for generation in range( 999 ):
	GAS_testing.breedPopulation( do_print=True )

# in order to test in Tournament mode:
#GAS_testing = GAS( parameters_testing )
#GAS_testing.tournament()
pass

# in order to do automated tests, do something like:
#GAS_complex_1 = GAS( parameters_complex_1 )
#GAS_complex_1.automatedTest()
#GAS_complex_2 = GAS( parameters_complex_2 )
#GAS_complex_2.automatedTest()

"""
The above automated test ran for about 21 days or about 509.5 hours on a laptop. Runtime specs are:
	- Python 3.6.2 (v3.6.2:5fd33b5, Jul  8 2017, 04:57:36) [MSC v.1900 64 bit (AMD64)] on win32
	- Intel Core i7-4712MQ @ 2.3GHz , 4 core/8 logical processors Hyper Threading, utilising 2 cores and 12% total CPU
	- Windows 7 Ultimate x64 bit, 8GB RAM
	- 38,880 runs of 7,776 combinations (total number of combinations is 11,664 but some are skipped as per the code above)
	
	
Some statistics and summary:

						Best	Average		Worst
Runtime					0.45 s	47.17 s		40,154.31 s
Best Score for run		-67		-146		-559
Average Score for run	-83.31	-323.14		-744.46
Worst Score for run		-107	-805		-1,519

- Optimal solution with score of -67 was reached 27 times, which is 0.0694 % success rate. Run times are (best/average/worst): 21.84 / 82.15 / 159.72
- Excellent solutions with score >= -70 were reached 343 times, which is 0.8822 % success rate. Run times are: 7.35 / 74.42 / 278.23
- Very good solutions with score >= -76 were reached 2082 times, whic is 5.3549 % success rate. Run times are: 3.53 / 83.61 / 10,676.38
- Good solutins with score >= -86 were reached 7299 times, which is 18.7732 % success rate. Run times are: 1.40 / 80.88 / 10,676.38


Impact Analysis

	- Generations				50		150		300
		Avg Time				16.56	43.54	81.42	high impact
		Avg Best Score for run	-151	-144	-143	low impact
	
	- Cross Min Step			0.05	0.15	0.35
		Avg Time				44.77	52.48	43.77	low impact
		Avg Best Score for run	-146	-143	-151	low impact
		
	- Cross Max Step			0.10	0.30	0.50
		Avg Time				45.75	51.32	44.89	low impact
		Avg Best Score for run	-152	-145	-144	low impact
		
	- Population Size			50		200		600
		Avg Time				12.03	38.92	90.58	high impact
		Avg Best Score for run	-228	-116	-94		high impact
		
	- Survival Rate				0.05	0.15	0.50
		Avg Time				23.07	35.67	82.79	high impact
		Avg Best Score for run	-157	-135	-145	low impact
		
	- Mutation Probability		0.00	0.05	0.15	0.50
		Avg Time				38.12	47.68	45.32	57.58	low impact
		Avg Best Score for run	-156	-145	-140	-142	low impact
	
	- Mutation Size				0.05	0.15	0.25
		Avg Time				41.30	45.76	54.47	low impact
		Avg Best Score for run	-147	-146	-145	low impact
	
	- Infuse Random				0		5		15		30
		Avg Time				40.10	49.33	46.86	52.40	low impact
		Avg Best Score for run	-108	-116	-162	-197	high impact
	
	
Best Overal Choices

In order to achieve excellent solutions in under a minute the following can be considered:
- Generations: It is an interesting mix of bell shaped curve and diminishing returns. The value should not be too high otherwise impacts run time.
- Cross Min Step: Doesn't seem to have noticable impact, however it's probably best to choose a relatively low value.
- Cross Max Step: Doesn't seem to have noticable impact either, however it's probably best to choose a middle-ish value between 0.35-0.50
- Population Size: It clearly has high impact on both run time and score. A classical example of a trade off between speed and result. Choose a value of a few hundred. It seems that diversity is a very important factor in finding solutions.
- Survival Rate: It has a high impact on run time, but not as much impact on score. It's best to choose a relatively low value, but not a minimal one.
- Mutation Probability: Doesn't seem to have a huge impact on either run time or score. But it does have a small contribution, so it is best to choose a modest value.
- Mutatation Size: Same as above.
- Infuse Random: This actually turns out to be not a very good feature of any model. It adversely affects the score, so set to 0 and do not use it, or use with a very modest value.

As a good model maybe use the following:
	Generations: 120
	"crossMinStep": 0.1
	"crossMaxStep": 0.4
	"populationSize": 500
	"survivalRate": 0.15
	"mutationProbability": 0.1
	"mutationSize": 0.12
	"infuseRandomToPopulation": 1
"""