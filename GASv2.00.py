"""
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

import random

class GAS():
	def __init__( self, _parameters ):
		self.resourceCount = int( _parameters[ "resourceCount" ] )
		self.populationSize = int( _parameters[ "populationSize" ] )
		self.population = []
		self.survivalRate = float( _parameters[ "survivalRate" ] )
		self.infuseRandomToPopulation = int( _parameters[ "infuseRandomToPopulation" ] )
		self.crossMaxStep = int( _parameters[ "crossMaxStep" ] )
		self.asapAlapMode = str( _parameters[ "asapAlapMode" ] )
		self.weightResourceSuccession = int( _parameters[ "weightResourceSuccession" ] )
		self.historyKeep = bool( _parameters[ "historyKeep" ] )
		self.historyRetryCount = int( _parameters[ "historyRetryCount" ] )
		self.history = []
		
		self.operationDurations = {}
		for i in _parameters[ "operationDurations" ]:
			if type( _parameters[ "operationDurations" ][ i ] ) is int:
				self.operationDurations[ i ] = int( _parameters[ "operationDurations" ][ i ] )
			elif type( _parameters[ "operationDurations" ][ i ] ) is list:
				self.operationDurations[ i ] = list( _parameters[ "operationDurations" ][ i ] )
			else:
				print( "Invalid operation duration: {}, type: {}\nTerminating".format( _parameters[ "operationDurations" ][ i ], type( _parameters[ "operationDurations" ][ i ] ) ) )
				return False
		
		self.operationCount = len( self.operationDurations )
		
		self.operationRelations = {}
		# A dictionary of two more nested dictionaries. The structure is operationRelations[ operation2 ][ operation1 ][ parameter ], where:
		# - "operation2" is the second operation in the relation
		# - "operation1" is the first operation in the relation
		# - "parameter" can be either of:
		# 	- "type" - for the type of relation, available types are:
		# 		- SS - start-to-start - the start of the first operation relates to the start of the second operation
		# 		- SE - start-to-end - ...
		# 		- ES - end-to-start - ...
		# 		- EE - end-to-end - ...
		# 	- "min" - the minimum time for the relation (for example, if the relation is ES and the min time is 1, that means that the second operation can start no sooner that 1 unit of time after the end of the first operation)
		# 	- "max" - the maximum time
		# 	- "weight" - a custom weight used to fine-tune the scoring of schedules, default is 1
		
		for op2 in _parameters[ "operationRelations" ]: # copy by value
			self.operationRelations[ op2 ] = {}
			for op1 in _parameters[ "operationRelations" ][ op2 ]:
				self.operationRelations[ op2 ][ op1 ] = dict( _parameters[ "operationRelations" ][ op2 ][ op1 ] )
		
		for op2 in self.operationRelations:
			for op1 in self.operationRelations[ op2 ]:
				if self.asapAlapMode == "normal":
					if self.operationRelations[ op2 ][ op1 ][ "min" ] == None and self.operationRelations[ op2 ][ op1 ][ "max" ] == None:
						self.operationRelations[ op2 ][ op1 ][ "min" ] = 0
				elif self.asapAlapMode == "asap":
					if self.operationRelations[ op2 ][ op1 ][ "min" ] != None:
						self.operationRelations[ op2 ][ op1 ][ "max" ] = self.operationRelations[ op2 ][ op1 ][ "min" ]
				elif self.asapAlapMode == "alap":
					if self.operationRelations[ op2 ][ op1 ][ "max" ] != None:
						self.operationRelations[ op2 ][ op1 ][ "min" ] = self.operationRelations[ op2 ][ op1 ][ "max" ]
		
		self.operationMaxTime = 0
		for op in range( self.operationCount ):
			self.operationMaxTime += max( self.operationDurations[ op ] )
		for op2 in self.operationRelations:
			for op1 in self.operationRelations[ op2 ]:
				rel_min = self.operationRelations[ op2 ][ op1 ][ "min" ] if self.operationRelations[ op2 ][ op1 ][ "min" ] != None else 0
				rel_max = self.operationRelations[ op2 ][ op1 ][ "max" ] if self.operationRelations[ op2 ][ op1 ][ "max" ] != None else 0
				self.operationMaxTime += max( abs( rel_min ), abs( rel_max ) )
				
		# calculate theoretical minimum and maximum scores - take into account all scoring methods!
		#!!!
				
	def getOperationDuration( self, _op, _r ):
		if type( self.operationDurations[ _op ] ) is int:
			return int( self.operationDurations[ _op ] )
		elif type( self.operationDurations[ _op ] ) is list:
			return int( self.operationDurations[ _op ][ _r ] )
		else:
			print( "Invalid operation duration: {}, type: {}\nTerminating".format( _parameters[ "operationDurations" ][ i ], type( _parameters[ "operationDurations" ][ i ] ) ) )
			return False
	
	def addRandomToPopulation( self, _n ):
		for n in range( _n ):
			start_times = [ random.randint( 0, self.operationMaxTime ) for o in range( self.operationCount ) ]
			resources = [ random.randint( 0, self.resourceCount - 1 ) for o in range( self.operationCount ) ]
			
			if self.historyKeep == True:
				for i in range( self.historyRetryCount ):
					if ( start_times, resources ) not in self.history:
						self.history.append( ( list( start_times ), list( resources ) ) )
						break
					start_times = [ random.randint( 0, self.operationMaxTime ) for o in range( self.operationCount ) ]
					resources = [ random.randint( 0, self.resourceCount - 1 ) for o in range( self.operationCount ) ]
			
			self.population.append( { "start_times": list( start_times ), "resources": list( resources ), "score": 0, "genome": "" } )
		
		return True
			
	def scorePopulation( self ):
		for p in self.population:
			p[ "score" ] = 0
			
			# Operation Relations
			for op2 in self.operationRelations:
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
							
					elif self.operationRelations[ op2 ][ op1 ][ "type" ] == "ES":
					
						if self.operationRelations[ op2 ][ op1 ][ "min" ] != None:
							threshold_min = start2 - ( end1 + self.operationRelations[ op2 ][ op1 ][ "min" ] )
							if threshold_min < 0: p[ "score" ] += threshold_min * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "asap":
							p[ "score" ] -= start2
							
						if self.operationRelations[ op2 ][ op1 ][ "max" ] != None:
							threshold_max = ( end1 + self.operationRelations[ op2 ][ op1 ][ "max" ] ) - start2
							if threshold_max < 0: p[ "score" ] += threshold_max * self.operationRelations[ op2 ][ op1 ][ "weight" ]
						elif self.asapAlapMode == "alap":
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
						print( "Invalid relation type {} at self.operationRelations[ {} ][ {} ][ 'type' ]".format( self.operationRelations[ op2 ][ op1 ][ "type" ], op2, op1 ) )
						return False
			
			p[ "score_operationRelations" ] = int( p[ "score" ] )
			
			
			# Resource Succession
			p[ "score_resourceSuccession" ] = int( p[ "score" ] )
			
			sorted_operations = []
			for i in range( self.operationCount ):
				sorted_operations.append( ( i, int( p[ "start_times" ][ i ] ), int( p[ "resources" ][ i ] ) ) )
			sorted_operations.sort( key = lambda x: ( x[ 2 ], x[ 1 ] ) )
			
			for i in range( 1, self.operationCount ):
				op1 = sorted_operations[ i-1 ][ 0 ]
				op2 = sorted_operations[ i ][ 0 ]
				r1 = sorted_operations[ i-1 ][ 2 ]
				r2 = sorted_operations[ i ][ 2 ]
				
				if r1 == r2:
					if p[ "start_times" ][ op2 ] < p[ "start_times" ][ op1 ] + self.getOperationDuration( op1, p[ "resources" ][ op1 ] ):
						p[ "score" ] -= self.weightResourceSuccession
							
			p[ "score_resourceSuccession" ] = int( p[ "score" ] - p[ "score_resourceSuccession" ] )
			
			
			# Fastest Resource (resource dependent operation durations)
			p[ "score_fastestResource" ] = int( p[ "score" ] )
			
			for op in range( self.operationCount ):
				p[ "score" ] -= self.getOperationDuration( op, p[ "resources" ][ op ] )
			
			p[ "score_fastestResource" ] = int( p[ "score" ] - p[ "score_fastestResource" ] )
			
		return True
			
	def calculatePopulationGenome( self ):
		resourceCount = self.resourceCount - 1 if self.resourceCount > 1 else 1
		
		for p in self.population:
			p[ "genome" ] = ""
			for i in range( self.operationCount ):
				p[ "genome" ] += self.numberToString( p[ "start_times" ][ i ], self.operationMaxTime )
				p[ "genome" ] += self.numberToString( p[ "resources" ][ i ], resourceCount )
		return True
			
	def numberToString( self, _number, _length ):
		number = int( _number )
		padding = int( _length - _number )
		probability = int( round( 100 * ( padding / _length ) ) )
		string = ""
		while number + padding > 0:
			if number == 0:
				string += "0"
				padding -= 1
				continue
			if padding == 0:
				string += "1"
				number -= 1
				continue
			if random.randint( 0, 100 ) < probability:
				string += "0"
				padding -= 1
			else:
				string += "1"
				number -= 1
		return string
		
	def breedPopulation( self ):
		self.scorePopulation()
		self.population.sort( key = lambda x: x[ "score" ], reverse = True )
		
		#print( "score: {}, start_times: {}, resources: {}".format( self.population[ 0 ][ "score" ], self.population[ 0 ][ "start_times" ], self.population[ 0 ][ "resources" ] ) )
		#if self.population[ 0 ][ "score" ] == 0:
		self.printBestNormalized()
		
		survivors = int( round( self.survivalRate * self.populationSize ) )
		for i in range( survivors, self.populationSize ):
			del self.population[ -1 ]
		
		if self.infuseRandomToPopulation > 0:
			self.addRandomToPopulation( self.infuseRandomToPopulation )
			self.calculatePopulationGenome()
			self.scorePopulation()
			
		self.calculatePopulationGenome()
		
		new_population = []
		for n in range( self.populationSize ):
			p1 = random.randint( 0, len( self.population ) - 1 )
			p2 = random.randint( 0, len( self.population ) - 1 )
		
			genome1 = str( self.population[ p1 ][ "genome" ] )
			genome2 = str( self.population[ p2 ][ "genome" ] )
			
			new_genome = str( self.crossTwoGenomes( genome1, genome2 ) )
			start_times, resources = self.genomeToValues( new_genome )
			
			if self.historyKeep == True:
				for i in range( self.historyRetryCount ):
					if ( start_times, resources ) not in self.history:
						self.history.append( ( list( start_times ), list( resources ) ) )
						break
					genome1 = str( self.population[ random.randint( 0, len( self.population ) - 1 ) ][ "genome" ] )
					genome2 = str( self.population[ random.randint( 0, len( self.population ) - 1 ) ][ "genome" ] )
					new_genome = str( self.crossTwoGenomes( genome1, genome2 ) )
					start_times, resources = self.genomeToValues( new_genome )
			
			new_population.append( { "start_times": list( start_times ), "resources": list( resources ), "score": 0, "genome": str( new_genome ) } )
		
		self.population.clear()
		self.population = list( new_population )
		
		return True
			
	def crossTwoGenomes( self, _genome1, _genome2 ):
		genome_length = len( _genome1 )
		index = 0
		result_genome = "";
		
		while True:
			step = random.randint( 1, self.crossMaxStep )
			if step > genome_length - ( index + 1 ):
				if random.randint( 0, 99 ) < 50:
					result_genome += _genome1[ index : ]
				else:
					result_genome += _genome2[ index : ]
				break
			if random.randint( 0, 99 ) < 50:
				result_genome += _genome1[ index : index + step ]
			else:
				result_genome += _genome2[ index : index + step ]
			index += step
		
		return result_genome
		
	def genomeToValues( self, _genome ):
		start_times = []
		resources = []
		segment = self.operationMaxTime + ( self.resourceCount - 1 if self.resourceCount > 1 else 1 )
		
		for i in range( self.operationCount ):
			st_from = i * segment
			st_to = i * segment + self.operationMaxTime
			r_from = i * segment + self.operationMaxTime
			r_to = ( i + 1 ) * segment
			
			start_times.append( _genome[ st_from : st_to ].count( "1" ) )
			resources.append( _genome[ r_from : r_to ].count( "1" ) )
			
		return start_times, resources
		
		
		
	def printBestNormalized( self ):
		min_start_time = min( self.population[ 0 ][ "start_times" ] )
		start_times = []
		for i in self.population[ 0 ][ "start_times" ]:
			start_times.append( i - min_start_time )
		print( "score: {}, s_opRel: {}, s_resSucc: {}, s_fastRes: {}, start_times: {}, resources: {}".format(
				self.population[ 0 ][ "score" ],
				self.population[ 0 ][ "score_operationRelations" ],
				self.population[ 0 ][ "score_resourceSuccession" ],
				self.population[ 0 ][ "score_fastestResource" ],
				start_times,
				self.population[ 0 ][ "resources" ]
			)
		)
		
	def dump( self, message ):
		for p in self.population:
			message += "{}, ".format( p[ "score" ] )
		print( message )
		
	def printSchedule( self ):
		for p in self.population:
			if p[ "score" ] == 0:
				print( "score: {}, start_times: {}, resources: {}".format( p["score"], p["start_times"],p["resources"] ) )
		
		
		

		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		



myOperationRelations = {
	0:{
		3:{ "type":"ES", "min":0, "max":0, "weight":1 }
	},
	4:{
		0:{ "type":"ES", "min":2, "max":2, "weight":1 },
		1:{ "type":"EE", "min":2, "max":2, "weight":1 }
	},
	2:{
		1:{ "type":"SS", "min":11, "max":11, "weight":1 }
	}
}

myOperationDurations = {
	0: [ 7, 5 ],
	1: [ 7, 5 ],
	2: [ 7, 5 ],
	3: [ 7, 5 ],
	4: [ 7, 5 ]
}

myParameters = {
	"resourceCount": 2,
	"populationSize": 200,
	"survivalRate": 0.2,
	"infuseRandomToPopulation": 0,
	"crossMaxStep": 20,
	"asapAlapMode": "normal",
	"weightResourceSuccession": 10,
	"historyKeep": False,
	"historyRetryCount": 30,
	"operationDurations": myOperationDurations,
	"operationRelations": myOperationRelations
}
myGAS = GAS( myParameters )
myGAS.addRandomToPopulation( myGAS.populationSize )


for i in range( 20 ):
	myGAS.breedPopulation()