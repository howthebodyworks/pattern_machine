ServerTreeGui.makeWindow(s);
//initialisation
Server.default = s = ~serverboot.(\internal, \motu);
Server.default = s = ~serverboot.(\internal, \builtin);
Server.default = s = ~serverboot.(\local, \motu);
Server.default = s = ~serverboot.(\local, \builtin);
StartUp.run;

~plotState = SwarmGraph.new(~swarm);
~plotState.stop;
//~swarm.params[\selfTracking] = 1.0;
~swarm.params[\selfTracking] = 0.0;
~swarm.params[\groupTracking] = 2.0;
~swarm.params[\momentum] = 1.03;
~swarm.params[\momentum] = 0.99;
~swarm.params[\noise] = 0.001;
~log.minPriority = -1;
~swarm.cookedFitnessMap.values.mean;
~swarm.cookedFitnessMap.values.variance;
(
fork {
	~globalOuts = Bus.new(\audio, 0, 1, s);
	//{~globalOuts.scope;}.defer;
	~phenogroup = Group.new(s);
	s.sync;
	~voxgroup = Group.new(~phenogroup, addAction: \addToHead);
	~outgroup = Group.new(~phenogroup, addAction: \addToTail);
	//~log = NullLogger.global;
	~log = PostLogger.global;
	//~log = FileLogger.global;
	~log.reject(\controlling);
	~log.reject(\moving);
	~log.minPriority = 1;
	~targetBus = Bus.new(\audio, 1, 1, s);
	~filename = ~zamples +/+ "music/flute/fluebitz.aiff";
	~buffer = Buffer.read(s, ~filename, 0);
	s.sync;
	~target = Synth.new(\ps_reson_saw, [\out, ~targetBus, \gate, 1, \ffreq, 800, \gain, 1, \pitch, 500, \rq, 0.2], target: ~phenogroup, addAction:\addToHead);
	//~target = Synth.new(\ps_sine, [\out, ~targetBus, \gate, 1, \gain, 1, \pitch, 500], target: ~phenogroup, addAction:\addToHead);
	//~spy = SpyBus.new.play(~target, ~targetBus);
	s.sync;
	//~spy.moveAfter(~target);
	/*******************/
	//limiter, to avoid little accidents
	SynthDef.new(\limi, {|bus| ReplaceOut.ar(bus, Limiter.ar(In.ar(bus),1,0.1))}).add;
	s.sync;
	~limi = Synth.after(~phenogroup, \limi, [~globalOuts]);
	//s.volume.gui;
	s.volume.volume= -20;
	//actual real work now: first choose the controller that will manage the synths
	~factory = PSSynthDefPhenotypeFactory.new(
		synthDef:\ps_reson_saw_lagged);
	~control = PSCompareSynthController.new(
		numChannels:1, log:~log, fitnessPollRate:2, leakCoef:0.5, maxPop:30,
	);
	~control.extraSynthArgs = [\lagtime, 1.0];
	~control.leakCoef = 0.05;
	//~control.listenSynthDef = \ps_judge_pitchamp_distance;
	//~control.listenSynthDef = \ps_judge_pitchamp_distance;
	//~control.listenSynthDef = \ps_judge_pitch_distance;
	//~control.listenSynthDef = \ps_judge_fft_distance_wide;
	//~control.listenSynthDef = \ps_judge_fft_distance_narrow;
	//~control.listenSynthDef = \ps_judge_convolution;
	//~control.listenSynthDef = \ps_judge_cepstral_distance;
	~control.listenSynthDef = \ps_judge_mfcc_distance;
	~control.play(~phenogroup, outBus: ~globalOuts, targetBus: ~targetBus);
	s.sync;
	1.wait;
	//now set up the "swarm" that will control their evolution
	~swarm = PSLocalOptimisingSwarm(
	//~swarm = PSOptimisingSwarm(
		(\populationSize: 30, 
		\chromosomeSize: 4,
		\clockRate: 20,
		\stepSize: 0.01,
		\selfTracking: 0.0,
		\groupTracking: 0.5,
		\momentum: 0.99,
		\neighboursPerNode: 5,
		\log: ~log,
		\individualConstructor: ~factory,
		//\maxdistance: 8, //a good distance for \ps_judge_pitchamp and scale_distance_to_similarity
		\maxdistance: 5, //a good distance for \ps_judge_mfcc_distance and scale_distance_to_similarity
	));
	//~swarm.scoreCooker = #[phenosynth, score_cookers, raw];
	//~swarm.scoreCooker = #[phenosynth, score_cookers, zero_peak];
	//~swarm.scoreCooker = #[phenosynth, score_cookers, scale_distance_to_similarity];
	~swarm.scoreCooker = #[phenosynth, score_cookers, invert_distance_to_similarity];
	//~swarm.scoreCooker = [\phenosynth, \score_cookers, \reverse_ranked];
	~swarm.play(~control);
	s.sync;
	[\phenogroup, ~phenogroup, \controlgroups, ~control.playGroup, ~control.listenGroup].postln;
};
)
//listen for a while.
//experiment
s.queryAllNodes;
~swarm.controller;
~swarm.neighbourTable;
~control.outBus;
~control.playBusses;
~control.fitnessBusses;
//{~swarm.plotFitness(raw:true);}.defer;
~swarm.params;
~swarm.initialChromosomeFactory.value;
~swarm.individualFactory.value;
~swarm.cookedFitnessMap;
~swarm.cookedFitnessMap.values.postln;
~swarm.rawScoreMap.values.postln;
~swarm.rawScoreMap.keys.asArray[1].hash.asHexString
//testing that things are going OK:
(
var best, worst, ranked;
ranked = ~swarm.rankedPopulation;
best = ranked[0];
worst = ranked[ranked.size-1];
[\best, ~swarm.rawScoreMap[best],~swarm.cookedFitnessMap[best], best.chromosomeAsSynthArgs].postln;
[\worst, ~swarm.rawScoreMap[worst],~swarm.cookedFitnessMap[worst], worst.chromosomeAsSynthArgs].postln;
nil;
)

//when you are bored, do a
~swarm.free;
~target.free;
~targetBus.free;
Library.atList([\phenosynth, \score_cookers, \zero_peak]).value(nil, ~swarm.rawScoreMap);
Library.atList([\phenosynth, \score_cookers, \reverse_ranked]).value(nil, ~swarm.rawScoreMap);

//these should only ever differ momentarily
~swarm.population.select(_.wallClockAge>0)
~swarm.controller.all[~swarm.population[0].identityHash].playBus.scope;
(
PSSynthDefPhenotype.chromosomeAsSynthArgs([0.0, 0.25, 0.75, 1]);
PSSynthDefPhenotype.synthArgsAsChromosome([\ffreq, 800, \gain, 1, \pitch, 800, \rq, 0.002]);
PSSynthDefPhenotype.synthArgsAsChromosome(PSSynthDefPhenotype.chromosomeAsSynthArgs([0.0, 0.25, 0.75, 1]));
PSSynthDefPhenotype.chromosomeAsSynthArgs(PSSynthDefPhenotype.synthArgsAsChromosome([\ffreq, 800, \gain, 1, \pitch, 800, \rq, 0.01]));
)
/**************************
 * TODO
 **************************
 
* multichannel
* per-voice synth params - e.g. a pan spread.
* meta-optimisation of the meta-heuristic.
	* annealing schedule
	* detecting the need to update noise parameters
	* GUI for noise params
* go to MOL ("many optimising liaisons") - choose random peer as neighbour.
* specific sample synth player
	* How can this sound sparser? Reward silence?
	* sample playing
	* sample recording
* handle feedback in reverberant environments in some smart way
* can I get rid of the PSSynthDefPhenotypeFactory now that I have extraSynthArgs in the controller class?
* should I put some methods in there to handle lagtime on the controller?
* Eliminate the phenotype factory malarkey; it should be all handled by the controller.
*/