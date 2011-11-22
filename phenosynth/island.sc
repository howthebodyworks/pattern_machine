PSIsland {
	//Islands accept populations of individuals, which can be anything
	//responding to \chromosome and \fitness.
	
	//we keep instance settings in a mutable Environment so that
	//generic function parameters can be passed to mutators, and they may
	//be modified at run-time without defining new functions
	var <>params;
	
	//Here are the functions that do the selection. these can be modified
	//by subclassing or by passing in functions at runtime.
	var <>deathSelector;
	var <>birthSelector;
	var <>mutator;
	var <>crossover;
	var <>initialChromosomeFactory;
	var <>individualFactory;
	var <>fitnessEvaluator;
	var <>terminationCondition;
	
	//This is the main state variable
	var <population;
	
	// this is another state variable. If I got one more I'd make it
	// a state *dictionary*
	var <iterations = 0;
	
	//some default population massaging functions
	//since we can't define naked functions in a classvar, we set these up in 
	//the *defaultOperators method.
	classvar <defaultDeathSelector;
	classvar <defaultBirthSelector;
	classvar <defaultMutator;
	classvar <defaultCrossover;
	classvar <defaultInitialChromosomeFactory;
	classvar <defaultIndividualFactory;
	classvar <defaultFitnessEvaluator;
	classvar <defaultTerminationCondition;
	
	//flag to stop iterator gracefuly.
	var playing = false;
	
	*initClass {
		StartUp.add({
			this.defaultOperators;
		});
	}
	
	// default values for that parameter thing
	// I wish I could do this with a literal instead of a method
	// because overriding is way awkward this way.
	*defaultParams {
		^(
			\deathRate: 0.1,
			\population: 100,
			\numParents: 2,
			\chromosomeMinLength: 20,
			\crossoverProb: 0.1,
			\individualClass: PSPhenotype,
			\mutationProb: 0.1,
			\mutationSize: 0.1,
			\stopIterations: 10000
		);
	}
	
	//where we define the default operators. These are vanilla functions,
	//even though the default implementations are static methods;
	//you might want to mix and match them, after all.
	*defaultOperators {
		//wow, it's kind of hard to have a graceful library of functions 
		//the _ make these return Functions, not function values.
		defaultDeathSelector = PSDeathSelectors.byRoulettePerRate(_,_,_);
		defaultBirthSelector = PSBirthSelectors.byRoulettePerTotal(_,_,_);
		defaultMutator = PSMutators.floatPointMutation(_,_,_);
		//this is a pretty awful crossover.
		defaultCrossover = PSCrossovers.uniformCrossover(_,_,_);
		defaultInitialChromosomeFactory = {|params|
			params.individualClass.newRandom;
		};
		defaultIndividualFactory = {|params, chromosome|
			params.individualClass.new(chromosome);
		};
		//not practical, just a sanity check - return the mean of the chromosome
		defaultFitnessEvaluator = {|params, phenotype|
			phenotype.fitness = phenotype.chromosome.mean;
		};
		defaultTerminationCondition = {|params, population, iterations|
			iterations > params.stopIterations;
		}
	}
	
	*new {|params|
		^super.newCopyArgs(
			this.defaultParams.updatedFrom(params);
		).init;
	}
	init {
		this.initOperators;
		population = List.new;
	}
	initOperators {
		deathSelector = this.class.defaultDeathSelector;
		birthSelector = this.class.defaultBirthSelector;
		mutator = this.class.defaultMutator;
		crossover = this.class.defaultCrossover;
		initialChromosomeFactory = this.class.defaultInitialChromosomeFactory;
		individualFactory = this.class.defaultIndividualFactory;
		fitnessEvaluator = this.class.defaultFitnessEvaluator;
		terminationCondition = this.class.defaultTerminationCondition;
	}
	add {|phenotype|
		population.add(phenotype);
	}
	remove {|phenotype|
		population.remove(phenotype);
	}
	populate {
		params.population.do({
			this.add(initialChromosomeFactory.value(params));
		});
	}
	evaluate {
		population.do({|phenotype|
			fitnessEvaluator.value(params, phenotype);
			phenotype.incAge;
		});
	}
	breed {|parentLists|
		parentLists.do({|parents|
			this.breedParents(parents);
		});
	}
	breedParents {|individuals|
		//take a nested list of parents and turn them in to new population.
		var newChromosome;
		params.crossoverProb.coin.if({
			newChromosome = crossover.value(
				params,
				individuals.collect({|i| i.chromosome;})
			);
		}, {
			newChromosome = individuals.choose.chromosome.copy;
		});
		newChromosome = mutator.value(params, newChromosome);
		this.add(individualFactory.value(params, newChromosome));
	}
	cull {|individuals|
		//take a list of the damned and kill them
		individuals.do({|i| this.remove(i);});
	}
	tend {
		// walk the population, doing all the things that GAs do.
		// this is a synchronous thing per default; if you want to do it
		// incrementally, that's your bag.
		var toCull, toBreed;
		var beforeFitness, afterFitness;
		this.evaluate;
		toCull = deathSelector.value(params, population);
		//[\culling, toCull].postln;
		this.cull(toCull);
		//afterFitness = population.collect(_.fitness).mean;
		//[\fitness_delta, afterFitness - beforeFitness].postln;
		toBreed = birthSelector.value(params, population);
		//[\breeding, toBreed].postln;
		this.breed(toBreed);
		iterations = iterations + 1;
	}
	fitnesses {
		^population.collect(_.fitness);
	}
	play {
		//The fire button. trigger this, and the simulation will run until it is bored
		var iterator;
		this.populate;
		playing = true;
		iterator = this.iterator;
		while {iterator.next } {
			//action happens in iterator
		};
	}
	free {
		playing = false;
	}
	iterator {
		/* Return a routine that does the work of triggering the work we want as
			long as things are supposed to be moving along. */
		^Routine.new({while(
			{
				(terminationCondition.value(
					params, population, iterations
				).not) && 
				playing 
			},
			{
				this.tend;
				[\iterations, iterations, this.fitnesses.mean].postln;
				true.yield;
			};
		);
		false.yield;}, stackSize: 1024);//seems to overflow easily?
	}
	reset {
		this.cull(population);
		this.populate;
		iterations = 0;
	}
}

PSRealTimeIsland : PSIsland {
	/* instead of checking my agents for fitness, I expect them to update
	themselves. I poll them at a defined interval to do tending.*/
	var <pollPeriod;
	var <worker;
	var clock;
	*new {| params, pollPeriod=1|
		//Why is pollPeriod not part of params?
		^super.new(params).init(pollPeriod);
	}
	*defaultOperators {
		super.defaultOperators;
		defaultDeathSelector = PSDeathSelectors.byRoulettePerRateAdultsOnly(_,_,_);
	}
	*defaultParams {
		var defParams = super.defaultParams;
		defParams.individualClass = PSEarSwarmPhenotype;
		^defParams;
	}
	*initClass {
		StartUp.add({
			this.defaultOperators;
		});
	}
	init {|newPollPeriod|
		pollPeriod = newPollPeriod;
		^super.init;
	}
	evaluate {
		//no-op in this class; they are realtime self-updating
	}
	play {
		/*note this does not call parent. If you can find a way of making this do
		the right thing with the generated routine while still caling the parent
		method, more power to you. Submit a patch. */
		var iterator;
		this.populate;
		clock = TempoClock.new(pollPeriod.reciprocal, 1);
		iterator = this.iterator;
		playing = true;
		worker = Routine.new({
			while {iterator.next;}
				{ 
					1.yield;
				}
		}).play(clock);
	}
	free {
		super.free;
		worker.free;
		clock.stop;
	}
}
