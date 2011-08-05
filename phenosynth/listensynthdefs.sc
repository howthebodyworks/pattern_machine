// based on MCLD's example MCLD_Genetic tests

PSBasicJudgeSynths {
  *initClass{
    StartUp.add({
      this.loadSynthDefs
    });
  }
  *loadSynthDefs {
    //first, a simple connector to siphon one bus into another.
    SynthDef.new(\jack, { |in, out|
      Out.ar(out, In.ar(in));
    }).add;
    // This judge is one of the simplest I can think of (for demo purposes) 
    // - evaluates closeness of pitch to a reference value (800 Hz).
    SynthDef.new(\ps_listen_eight_hundred, { |in, out, active=0, t_reset=0, targetpitch=800|
      var testsig, comparison, integral, freq, hasFreq;
      testsig = LeakDC.ar(Mix.ar(In.ar(in, 1))).poll(1, \sig);
      # freq, hasFreq = Pitch.kr(testsig).poll(1, \pitch);
      comparison = hasFreq.if(
        (200 - ((freq - targetpitch).abs)).max(0),
        0
      ).poll(1, \comp);
       // "0" if hasFreq==false because we don't want to encourage quietness

      // Divide by the server's control rate to bring it within a sensible range.
      comparison = comparison / ControlRate.ir;
    
      // Default coefficient of 1.0 = no leak. When t_reset briefly hits nonzero, the integrator drains.
      integral = Integrator.kr(comparison * active, if(t_reset>0, 0, 1));
      Out.kr(out, integral);
    }).add;
  }
}
