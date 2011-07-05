/*
TODO:

* Note that Instr loading is buggy - see http://new-supercollider-mailing-lists-forums-use-these.2681727.n2.nabble.com/Instr-calling-Crashes-SC-td4165267.html

  * you might want to use HJH's Instr.loadAll; workaround.
  
* move patch creation into a "play" or "go" method.
* Handle "free controls", values that are passed in live by the user. (esp for
  triggers)
  
  * alter chromosome if Specs are changed through UI or any other means, using
    all that Dependent business

* Give the faintest of indications that I do care about tests
* work out a better way to handle non-chromosome'd arguments. right now I
  handle, e.g. SampleSpecs by passing in a voxDefaults array, and triggers by
  introspecting a trigger array. But this is feels ugly compared to wrapping
  an Instr in a function and specifying the missing arguments by lexical
  closure. At the least I could provide lists of specs for each of the
  evolved, free, fixed and trigger parameters, and provide the usual accessors
  to each. (Compare static, fixed and control specs)
* user EnvelopedPlayer to make this release nicely instead of Triggers.
* Use PlayerMixer to make this fly - or .patchOut?
* Make a LiveGenoSynth to manage a running population. (probably not, that
  should be left to GA infrastructure)
* allow custom evolvability mappings and starting chromosome.
* I've just noticed that MCLD has been facing the same problem and made
  classes similar in spirit to mine, as regards selecting the phenotypes
  rather than genotypes, as the NLTK does:
  http://swiki.hfbk-hamburg.de:8888/MusicTechnology/778
  
  * In fact he has made a far more diabolically clever one: http://www.mcld.co.uk/supercollider/
  
* put these guys in the correct groups
* do free/cleanup logic
* give fitness more accumulatey flavour using Integrator

CREDITS:
Thanks to Martin Marier and Crucial Felix for tips that make this go, and
James Nichols for the peer pressure to do it.
*/

Genosynth {
  /* A factory for Phenosynths wrapping a given Instr. You would have one of
  these for each population, as a rule.*/
  var <voxInstr, <voxDefaults, <listenInstr, <listenExtraArgs, <sourceGroup, <outBus, <numChannels, <voxOut, <chromosomeMap, <triggers, <listenInstr, <evalPeriod, <voxGroup, <listenGroup, <outGroup;
  classvar <defaultVoxInstr="phenosynth.vox.default";
  classvar <defaultListenInstr="phenosynth.listeners.default";

  *new { |voxName, voxDefaults, listenName, listenExtraArgs, sourceGroup, outBus, numChannels|
    //voxName - name, or Instr, that will be source
    //voxDefault - array of default args to voxName
    //listenName, listenExtraArgs - like voxName, but for listening Instr
    //sourceGroup - a group that we must come after (Should we jsut supply the gourp to be in?)
    ^super.newCopyArgs(
      (voxName ? Genosynth.defaultVoxInstr).asInstr,
      (voxDefaults ? []),
      (listenName ? Genosynth.defaultListenInstr).asInstr,
      (listenExtraArgs ? []),
      sourceGroup,
      (outBus ? 0),
      (numChannels ? 1)).init;
  }
  init {
    this.debug;
    this.dump;
    [voxInstr, voxDefaults, listenInstr, listenExtraArgs].postln;
    chromosomeMap = this.class.getChromosomeMap(voxInstr);
    // pad voxDefaults out to equal number of args
    voxDefaults = voxDefaults.extend(voxInstr.specs.size, nil);
    triggers = this.class.getTriggers(voxInstr);
    /*We give default values to any triggers without a one, or they
    get saddled with an inconvenient BeatClockPlayer*/
    triggers.do({|trigIndex, i| (voxDefaults[trigIndex].isNil).if(
      {voxDefaults[trigIndex] = 1.0;})
    });
  }
  play {
    voxGroup = Group.new(sourceGroup, addAction: \addAfter);
    listenGroup = Group.new(this.voxGroup, addAction: \addAfter);
    outGroup  = Group.new(this.listenGroup, addAction: \addAfter);
    voxOut = Patch(
      "phenosynth.util.master",
      [PlayerInputProxy.new, 1]
    ).play(/*bus: outBus, */group: this.outGroup);//straight-thru bus patch
  }
  spawnNaked { |chromosome|
    //just return the phenosynth itself, without listeners
    ^Phenosynth.new(this, voxInstr, voxDefaults, chromosomeMap, triggers, chromosome);
  }
  spawn { |chromosome|
    //return a listened phenosynth
    ^ListenPhenosynth.new(this, voxInstr, voxDefaults, chromosomeMap, triggers, listenInstr, evalPeriod, listenExtraArgs, chromosome);
  }
  *getChromosomeMap {|newInstr|
    /*use this to work out how to map the chromosome array to synth values,
    ignoring any fixed values, sampleSpecs, or any other kind of
    NonControlSpec
    TODO: Work out how to do this with duck typing.*/
    ^newInstr.specs.indicesSuchThat({|item, i|
      (item.isKindOf(NonControlSpec).not);});
  }
  *getTriggers {|newInstr|
    /*The other input type we might care about is a trigger. I don't know why
    you'd want more than one, but it's more symmetrical if we assume a list,
    so ...*/
    ^newInstr.specs.indicesSuchThat({|item, i|
      item.isKindOf(TrigSpec)});
  }
}

Phenosynth {
  /* wraps an Instr with a nice Spec-based chromosome interface. This should
  be an inner class of GenoSynth, really, but SC doesn't namespace in that
  way.*/
  var <genosynth, <voxInstr, <voxDefaults, <chromosomeMap, <triggers, <voxPatch;
  var <chromosome = nil;
  *new {|genosynth, voxInstr, voxDefaults, chromosomeMap, triggers, chromosome|
    //This should only be called through the parent Genosynth's spawn method
    ^super.newCopyArgs(genosynth, voxInstr, voxDefaults, chromosomeMap, triggers).init(chromosome);
  }
  init {|chromosome|
    this.createPatch;
    this.chromosome_(chromosome);
  }
  createPatch {
    voxPatch = Patch.new(voxInstr, voxDefaults);
  }
  chromosome_ {|newChromosome|
    /* do this in a setter to allow param update */
    newChromosome.isNil.if({
      newChromosome = {1.0.rand}.dup(chromosomeMap.size);
    });
    chromosome = newChromosome;
    chromosomeMap.do(
      {|specIdx, chromIdx|
        voxPatch.specAt(specIdx).map(chromosome[chromIdx]);
      }
    );
  }
  trigger {
    triggers.do({|item, i| 
      voxPatch.set(item, 1);});
  }
  play {
    genosynth.play;
    /*********************/
    voxPatch.play(group: genosynth.voxGroup);
    "hoo".postln;
    genosynth.voxOut.patchIns.dump;
    genosynth.voxOut.patchIns[0].dump;
    genosynth.voxOut.patchOut.dump;
    voxPatch.patchOut.connectTo(genosynth.voxOut.patchIns[0]);
    this.trigger();
  }
}

ListenPhenosynth : Phenosynth {
  var <listenInstr;
  var <listenExtraArgs;
  var <evalPeriod = 1;
  var <fitness = 0;
  var <>age = 0;
  var <reportingListenerPatch, <reportingListenerInstr, <listener;
  *new {|genosynth, voxInstr, voxDefaults, chromosomeMap, triggers, listenInstr, evalPeriod=1, listenExtraArgs, chromosome|
    //This should only be called through the parent Genosynth's spawn method
    ^super.newCopyArgs(genosynth, voxInstr, voxDefaults, chromosomeMap, triggers).init(chromosome, listenInstr, evalPeriod, listenExtraArgs);
  }
  init {|chromosome, listenInstr_, evalPeriod_, listenExtraArgs_|
    listenInstr = (listenInstr_ ? Genosynth.defaultListenInstr).asInstr;
    listenInstr.isNil.if({Error("no listenInstr" + listenInstr_ + Genosynth.defaultListenInstr ++ ". Arse." ).throw;});
    evalPeriod = evalPeriod_ ? 1.0;
    listenExtraArgs = listenExtraArgs_ ? [];
    super.init(chromosome);
  }
  createPatch {
    super.createPatch;
    (["ListenPhenosynth.createPatch", evalPeriod] ++ listenExtraArgs).postln;
    listener = Patch(listenInstr, [
        PlayerInputProxy.new,
        evalPeriod
      ] ++ listenExtraArgs//where we inject other busses etc
    );
    reportingListenerInstr = ReportingListenerFactory.make({
      |time, value|
      fitness = value;
      age = age + 1;
      //this.dump;
      //["updating correlation", this.hash, time, value, age].postln;
    });
    reportingListenerPatch = Patch(
      reportingListenerInstr, [
        listener,
        evalPeriod
      ]
    );
  }
  play {
    /*play reportingListener and voxPatch.*/
    ["LP.play",0].postln;
    super.play;
    ["LP.play",1].postln;
    reportingListenerPatch.play(
      group: genosynth.voxGroup);
    ["LP.play",2].postln;
    voxPatch.dump;
    ["LP.play",3].postln;
    voxPatch.patchOut.dump;
    ["LP.play",4].postln;
    listener.patchIns.dump;
    listener.patchIns[0].nodeControl.dump;
    ["LP.play",5].postln;
    //voxPatch.patchOut.connectTo(listener.patchIns[0]);
    //this.trigger;
    ["LP.play",6].postln;
  }
}

ReportingListenerFactory {
  /*Instrs like having names, so we make some on demand to keep things clean.
  TODO: I'm not totally sure if this is neccessary, and should check that
  after the current deadline crunch.*/
  classvar counter = 0;
  *make {|onTrigFn, evalPeriod=1|
    /*takes a function of the form {|time, value| foo} */
    var newInstr;
    newInstr = Instr(
      "phenosynth.reportingListener.volatile." ++ counter.asString,
      {|in, evalPeriod=1|
        LFPulse.kr((evalPeriod.reciprocal)/2).onTrig(onTrigFn, in);
        // actually just be quiet please
        Silent.ar
      },
      [\audio], \audio
    );
    counter = counter+1;
    ^newInstr;
  }
}
