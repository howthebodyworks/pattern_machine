Server.default = s = ~serverboot.(\internal, \builtin);
(fork {
	var	observedFftBuffer,targetFftBuffer, bothSignals,
		observedBus, targetBus, matchOut,
		template, comparer, candidate;
	observedFftBuffer = Buffer.alloc(s, 128);
	targetFftBuffer = Buffer.alloc(s, 128);
	bothSignals = Bus.new(\audio, 0, 2, s);
	observedBus = Bus.newFrom(bothSignals, 0, 1);
	targetBus = Bus.newFrom(bothSignals, 1, 1);
	matchOut = Bus.control(s, 1);
	s.sync;
	comparer = {|leak=0.1|
		var targetfftchain, obsfftchain, target, observed, localTargetFftBuffer, localObservedFftBuffer;
		
		target  = In.ar(targetBus, 1);
		observed = In.ar(observedBus, 1);

		// localTargetFftBuffer = LocalBuf.new(128,1);
		// localObservedFftBuffer = LocalBuf.new(128,1);
		
		localTargetFftBuffer = targetFftBuffer;
		localObservedFftBuffer = observedFftBuffer;

		targetfftchain = FFT(localTargetFftBuffer, target);
		obsfftchain = FFT(localObservedFftBuffer, observed);

		// Smear the FFT a little to avoid being trapped in bins
		// targetfftchain = PV_MagSmear(targetfftchain, 5);
		// obsfftchain = PV_MagSmear(obsfftchain, 5);
		
		leak = (leak**(ControlRate.ir.reciprocal));
		//replace me with a straight 1-pole:
		Integrator.kr(FFTDiffMags.kr(targetfftchain, obsfftchain) * (1-leak),  leak);
	}.play(target:s, addAction: \addToTail, outbus: matchOut);
	
	SynthDef.new(
		\fft_dist_test_synth,
		{ |out=0, gate=0, t_reset=0, pitch=800, ffreq=500, rq=0.5, gain=1.0, delay=0.0|
			Out.ar(out, 
				DelayN.ar(
					Resonz.ar(
						Saw.ar(pitch, gain),
						ffreq,
						rq
					),
					delaytime: delay
				)
			);
		}
	).add;

	s.sync;
	template = Synth.new(
		\ps_reson_saw,
		[\out, targetBus, \gate, 1, \pitch, 400, \ffreq, 600, \rq, 0.3, \gain, 0.5, \delay, 0.0321207],
		target: s,
		addAction: \addToHead
	);
	candidate = Synth.new(
		\ps_reson_saw,
		[\out, observedBus, \gate, 1, \pitch, 400, \ffreq, 600, \rq, 0.3, \gain, 0.5, \delay, 0],
		target: s,
		addAction: \addToHead
	);

	Routine.new({
		while( true, {matchOut.get(_.postln);
		1.yield;})
	}).play;
	~bothSignals = bothSignals;
	~observedBus = observedBus;
	~observedFftBuffer = observedFftBuffer;
	~targetFftBuffer = targetFftBuffer;
	~candidate = candidate;
	{
		~bothSignals.scope;
		FreqScope.new(busNum: ~observedBus);
		~observedFftBuffer.plot;
		~targetFftBuffer.plot;
	}.defer(2.0);
})

~observedFftBuffer.loadToFloatArray(action: { |array| ~obsfftbufasarray = array; { var thisguy = array; thisguy.plot; }.defer;});
~targetFftBuffer.loadToFloatArray(action: { |array| ~targetfftbufasarray = array; { var thisguy = array; thisguy.plot; }.defer;});
~targetfftbufasarray;
~obsfftbufasarray;
~candidate.set(\pitch, 400, \ffreq, 600, \rq, 0.3, \gain, 0.5);
~candidate.set(\pitch, 27, \ffreq, 4800, \rq, 0.01, \gain, 0.5);