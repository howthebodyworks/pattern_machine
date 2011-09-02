(
//initialisation
s=Server.default;
~globalOuts = Bus.new(\audio, 0, 2);
//~globalIns = Bus.new(\audio, s.options.numOutputBusChannels, 1);//better way to get first audio in?
~globalIns = Bus.audio(s, 1)
~voxgroup = Group.new(s);
~outgroup = Group.after(~voxgroup);
//limiter, to avoid little accidents
~limidef = SynthDef.new(\limi,{|bus| ReplaceOut.ar(bus, Limiter.ar(In.ar(bus),1,0.1))}).send;
~limi = Synth.tail(~outGroup, \limi, [~globalOuts]);
s.volume.gui;
s.volume.volume= -20;
//actual real work nowl first choose the controller that will manage the synths
~control = PSEarSwarmController(s, ~globalOuts);
//now set up the "isalnd" that will control their evolution
~island = PSEarSwarmIsland.new((\population: 30), controller:~control);
~island.play;
//
~island.free;
~island.population.select(_.wallClockAge>0)
//listen for a while.

//testing that things are going OK:
~island.fitnesses.mean;
~island.population.collect({|i| i.wallClockAge}).mean;
~island.population.collect({|i| i.logicalAge}).mean;
//these should only ever differ momentarily
~island.population.size;
~island.population[0];
~island.controller.all[~island.population[0].identityHash].playBus.scope
~globalOuts.scope
//when you are bored, do a
~island.free;
//(you might need to do it twice. I'm working on that.)
)
(
//multichannelising tests
SynthDef.new(\testoffsets, {|outs| Out.ar(outs, DC.ar(2.pow((0..3))))}).add;
SynthDef.new(\sumins, {|ins, out| Out.kr(out, A2K.kr(Mix.ar(In.ar(ins))))}).add;
~mctestouts = Bus.audio(s, 4);
~mcrezout = Bus.control(s, 1);
~mcplaygroup = Group.head(s);
~mclistengroup = Group.after(~mcplaygroup);
~mcplaysynth = Synth.new(\testoffsets, [\outs, ~mctestouts], ~mcplaygroup);
~mclistensynth = Synth.new(\sumins, [\ins, ~mctestouts, \out, ~mcrezout], ~mclistengroup);
~mcrezout.get(_.postln);
(1..17).do({|numChannels|
  SynthDef.new('jack$' ++ numChannels.asString, { |in, out|
	Out.ar(out, In.ar(in, numChannels));
  }).add;
});
PSSynthDefPhenotype.map
"nameBase" ++ "$$" ++ 4.asString
)
(
~playGroup = Group.new(s);
~listenGroup = Group.after(~playGroup);
~audioBus = Bus.audio(s, 1);
~fitBus = Bus.control(s,1);
SynthDef.new(\sawy, {|out, freq| Out.ar(out, Saw.ar(freq));}).add;
~play = Synth.new(\sawy, [\out, ~audioBus, \freq, 300], ~playGroup);
~judge = Synth.new(\ps_conv_eight_hundred, [\in, ~audioBus, \out, ~fitBus, \i_leakcoef, 0.5], ~listenGroup);
~play.set(\freq, 850);
~fitBus.get(_.postln);
)
(
//How the controller works, nuts-and-bolts
s=Server.default;
~globalOuts = Bus.new(\audio, 0, 2);
~control = PSListenSynthSwarmController.new(s, ~globalOuts);
~ind = PSSynthDefPhenotype.newRandom;
~control.playIndividual(~ind);
~control.freeIndividual(~ind);
~ind.mappedArgs
~ind.identityHash;
~ind.chromosome;
10.do({~control.playIndividual(PSSynthDefPhenotype.newRandom)});
~control.all.do({|a,b,c| [a,b,c].postln;});
)
/*
NOTES:


TODO:

* infrastructure
	* ensure Groups are also freed.
	* allow a seed-bank supporting far more genomes than can be simultaneously simulated. (I.e. keep a much larger population, but only simulate a part of them at once
	* use wrapping infrastructure to simplify the listensynth definitions.
		* support multi-channel listeners (In.ar is hardcoded to 1 channel atm) 

	* sort out the interactions of all these different tick rates and periods.
	* Handle "free controls", values that are passed in live by the user. (esp for
	  triggers)
	* alter chromosome if Specs are changed through UI or any other means, using
		all that Dependent business
	* support "fitness injection" - doing custom pre-processing on fitness?
		* so much more complex than simply overriding the calss. do that later.
	* non-accumulating, genotype-style selection
		* but I don't personally need that.
	* envelope synth deletion
		* use Synth doneActions and per-listener groups to free all resources on demand
		* don't bother freeing the "jack" synths where population is constant.
		* watch out for those double /n_frees - might break something.
	* serialize phenotypes to disk so evolution can be resumed.
	* chromosome management
		* provide a way to unwarp as well as warp chromosomes
		* go to all-binary chromosomes for increased happiness and elegance/
	* handle zero-fitness populations in the parent and death selector
	* provide a "migration phase" in which to check for extinction and restock.

* Give the faintest of indications that I do care about tests


* my earswarm
	* normalise fitness gain w/respect to energy expenditure (i.e. amplitude)
	* LFOs
		* support creatures which vocalise only sporadically (saving CPU, or at least saving earspace)
	* give lifespans using the exponential distribution \lambda \e ^-\lambda \e
	*doesnt' apply ATM but might with different regims:
		* scale birthRate and deathRate so that they fit eventual fitness
		* reseed population when they all die

* allow custom evolvability mappings and starting chromosome.
* I've just noticed that MCLD has been facing the same problem and made
	classes similar in spirit to mine, as regards selecting the phenotypes
	rather than genotypes, as the NLTK does:
	http://www.mcld.co.uk/supercollider/ - see also https://github.com/howthebodyworks/MCLD_Genetic

CREDITS:
Thanks to Martin Marier and Crucial Felix for tips that make this go, and
James Nichols for the peer pressure to do it.


*/
