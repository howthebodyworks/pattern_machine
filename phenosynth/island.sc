PSIsland {
  //Islands accept populations of individuals, which can be anything
  //responding to \chromosome and \fitness.
  var deathSelector;
  var birthSelector;
  var mutator;
  var crossover;
  var initialChromosomeFactory;
  var individualFactory;
  var fitnessEvaluator;
  var terminationCondition;
  
  //we keep instance settings in a mutable Environment so that
  //generic function parameters can be passed to mutators, and they may
  //be modified at run-time without defining new functions
  var <>params;
  
  //This is the main state variable
  var <population;
  
  // this is another state variable. If I got one more I'd make it
  // a state *dictionary*
  var <iterations = 0;
  
  //this is a Condition to indicate when the thing is done, since you
  //probably don't want it happening in a main thread.
  var doneFlag;
  
  //some default population massaging functions
  //since we can't define naked functions in a classvar, we set these up in 
  //the *defaultOperators method.
  classvar defaultDeathSelector;
  classvar defaultBirthSelector;
  classvar defaultMutator;
  classvar defaultCrossover;
  classvar defaultInitialChromosomeFactory;
  classvar defaultIndividualFactory;
  classvar defaultFitnessEvaluator;
  classvar defaultTerminationCondition;
  
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
      \stopIterations: 10000,
      \delay: 0.0001 //delay in seconds between cycles to stop explosions
    );
  }
  
  //where we define the default operators. These are vanilla functions,
  //even though the default implementations are static methods;
  //you might want to mix and match them, after all.
  *defaultOperators {
    defaultDeathSelector = {|params, population|
      PSDeathSelectors.byRoulettePerRate(params, population);
    };
    defaultBirthSelector = {|params, population|
      PSBirthSelectors.byRoulettePerTotal(params, population);
    };
    defaultMutator = {|params, chromosome|
      PSMutators.floatPointMutation(
        params,
        chromosome);
    };
    defaultCrossover = {|params, chromosomes|
      //this is a pretty awful crossover.
      PSCrossovers.uniformCrossover(params, chromosomes);
    };
    defaultInitialChromosomeFactory = {|params|
      params.individualClass.newRandom;
    };
    defaultIndividualFactory = {|params, chromosome|
      params.individualClass.new(chromosome);
    };
    defaultFitnessEvaluator = {|params, phenotype|
      //baseline sanity check - jsut return the mean of the chromosome
      phenotype.fitness = phenotype.chromosome.mean;
    };
    defaultTerminationCondition = {|params, population, iterations|
      iterations > params.stopIterations;
    }
  }
  
  *new {|params,
    deathSelector,
    birthSelector,
    mutator,
    crossover,
    initialChromosomeFactory,
    individualFactory,
    fitnessEvaluator,
    terminationCondition|
    ^super.newCopyArgs(
      deathSelector ? defaultDeathSelector,
      birthSelector ? defaultBirthSelector,
      mutator ? defaultMutator,
      crossover ? defaultCrossover,
      initialChromosomeFactory ? defaultInitialChromosomeFactory,
      individualFactory ? defaultIndividualFactory,
      fitnessEvaluator ? defaultFitnessEvaluator,
      terminationCondition ? defaultTerminationCondition,
      params ? this.defaultParams
    ).init;
  }
  init {
    population = List.new;
    doneFlag = Condition.new(false)
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
    //walk the population, doing all the things that GAs do.
    // this is a synchronous thing per default; if you want to do it
    // incrementally, that's your bag.
    var toCull, toBreed;
    this.evaluate;
    toCull = deathSelector.value(params, population);
    this.cull(toCull);
    toBreed = birthSelector.value(params, population);
    this.breed(toBreed);
    iterations = iterations + 1;
  }
  go {
    //The fire button. trigger this, and the simulation will run until it is bored
    var delay;
    doneFlag.test = false;
    this.populate;
    while(
      {
        terminationCondition.value(
          params, population, iterations
        ).not 
      },
      {
        this.tend;
        [\iterations, iterations].postln;
      }
    );
  }
  reset {
    this.cull(population);
    this.populate;
    iterations = 0;
  }
}