/*
Markovy (Wavvie-lite)

TODO:
* seeding
* reversing
* multistrip
* time decoherence
* correlation matrix re-generation
* centrepoint management
* magnitude of evolution
* updating scales. ?.
* updating tempos. ?.
* heartbeat
*/

ServerTreeGui.makeWindow(s);
Server.default = PS.serverboot.(\local, \builtin);
(
var samples,
	server,
	state;

server = Server.default;
state = (
	sampleDur: 60.0,
	server: server,
	inbus: server.inputBus.subBus(0,1),
	outbus: server.outputBus.subBus(0,2),
	clock: TempoClock.new(140/60),
);

~state=state;
state.server.waitForBoot({
	var samplingstrip, samples;
	samples = this.executeFile(
		PS.scriptpath +/+ "wavvie_samples.scd").value(state);
	CmdPeriod.doOnce({ samples.free});
	this.executeFile(PS.scriptpath +/+ "wavvie_synths.scd").value(state);
	s.sync;
	samplingstrip = PSSamplingStrip.new(
		state:state,
		samples: samples,
		inbus: state.inbus,
		outbus:state.outbus,
		clock: state.clock);
	CmdPeriod.doOnce({ samplingstrip.free});

	state.make({
		~samplingstrip = samplingstrip;
		~samples = samples;
		s.sync;
		{samplingstrip.rec(10.0);}.defer(1.0);
		~lfo2del = 0.0;
		~lfomodamp = 1/2;
		~param = 1;
		~interval = 2;
		~buffers = ["a", "b", "c"];
		~cluster = 4;
	});
});
)
(
	var state = ~state, paramspace, controlchan, scheduletask, playfunc, mapper;
	state.paramspace = paramspace = PSParamSpace(\wavviebasic);
	paramspace.newParam(\lfomodf, PSLookupSpec([1/4,1/3,1/2,1,2,3,4,6]));
	paramspace.newParam(\lfobasef, PSLookupSpec([1/4,1/3,1/2,1,2,3,4,6]));
	paramspace.newParam(\lfomodamp, [0.001, 1.0, \exp]);
	paramspace.newParam(\lfo2amp, ControlSpec(minval:-0.1, maxval:0.1, default:0));
	paramspace.newParam(\lfo2grain, ControlSpec(minval:-0.1, maxval:0.1, default:0));
	paramspace.newParam(\lfo2pan, ControlSpec(minval:-0.1, maxval:0.1, default:0));
	paramspace.newParam(\timeago, PSLookupSpec([1,2,3,4,8,12,16]));
	paramspace.newParam(\grainsize, PSLookupSpec([1,2,4,8,16,32]/32));
	paramspace.newParam(\pitchrate, PSLookupSpec([1/2,1,2]));
	paramspace.newParam(\combed, [0.001, 1.0, \exp]);
	paramspace.newParam(\pan, \pan);
	paramspace.newParam(\windowRandRatio, [0.0,1.0, \lin, 0, 0.5]);
	paramspace.newParam(\allpdelayratio, [0.1,1.0, \lin,0,0.25]);
	paramspace.newParam(\allpdecayratio, [1,8,\exp,0,1]);
	paramspace.newParam(\posrate, PSLookupSpec([-1,-1/2,-1/4,0,1/4,1/2,1]));
	paramspace.newParam(\sustainDur, ControlSpec(minval:0.25, maxval:8, warp:\exp, default:2));
	paramspace.newParam(\delta, PSLookupSpec([1,2,4,8,16,32]/8));

	state.mapper = mapper = PSMetaParamMap.new(
		inDims:2, outDims:paramspace.newPresetDefault.size);

	state.controlchan = controlchan = PSHawkesLemurControlChan.new(
		trace:false, state: state);
	state.playfunc = playfunc = {
		\playing.postcs;
		(Pfunc({|ev|
			ev.putAll(paramspace.eventFromPreset(state.mapper.value([
				(ev.generation/(state.cluster)).fold(0,1),
				ev.mark], 0, 1)));
			ev.delta = ev.delta * ((state.decohere/2.0).rand2+1);
			ev.db = (ev.generation) * (state.decay) + (ev.db?0);
			[\pfunc,ev].postcs;
			ev;
		}) <> PGeomRepM(Pbind(
			\mark, //Pseed(4,
				PMarkovChain.auto(
					disorder:0.2,
					nstates: 9,
					initState:\rand,
					halt:nil,
					ordertype: \drunk,
					expressions: \unit
				//)
			),
			\generation, Pseries.new,),
			Pfunc({state.cluster})
		) <> (state.samplingstrip.basePattern)
		).play(
			clock: state.clock,
			protoEvent: (
				instrument: \ps_bufgrain_type_2__1x2,
				sendGate: false,
				lfophase: 0,
				db: -10.0,
				overlaps: 4,
			),
			quant:1
		);
	};
	scheduletask = Routine({
		var ctr=0;
		inf.do({
			ctr = (ctr + 1) % (state.interval);
			//[\ctr, ctr, thisThread.beats].postln;
			(ctr==0).and(state.interval>0).if({
				playfunc.value;
			});
			controlchan.heartbeat(1);
			state.clock.sched(0.25, {controlchan.heartbeat(1);});
			1.yield;
		})
	}).play(state.clock, 1);
	controlchan.bangCallback={playfunc.value};
)
~state.paramspace.newPresetDefault
~state.samplingstrip.rec(1.0);
~state.samplingstrip.rec(60.0);
~state.samplingstrip.sourceBuf(3);
~state.samplingstrip.sourceBuf(\tuneful,4);
~state.samplingstrip.sourceBuf(\choral,1);
~state.samplingstrip.sourceBuf(\people,0);
~state.samplingstrip.sourceBuf(\siren,0);
~state.samplingstrip.sourceBuf(\desolation,0);
~state.samples.at(\tuneful, 2);
~state.interval=2
i.state;
i.intAddr;
OSCFunc.trace(false);
~state.seed;
~state.clock.postcs;
~state.postcs;
