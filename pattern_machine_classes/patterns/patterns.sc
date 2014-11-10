//Handy psudopatterns for Patterns that I would like to be a little tidier.
PSwrand {
	*new {|weightedList, repeats=1|
		var expressions = Array.new(weightedList.size/2);
		var weights = Array.new(weightedList.size/2);
		weightedList.pairsDo({|weight, expression|
			weights.add(weight);
			expressions.add(expression);
		});
		weights = weights.normalizeSum;
		^Pwrand.new(expressions, weights, repeats);
	}
}
P1bind {
	//P-one-bind embeds the arguments as a single event in the stream ONCE
	//events embed unpredictably - e.g. eternally repeating if you embed them in parallel, otherwise just once.
	//note events with better defaults, or an event subclass,
	// might be able to do this better.
	// Shouldn't this be EmbedOnce, or OneShot?
	*new { arg ... pairs;
		^Pfin(1, Pbind(*pairs))
	}
}
P1event : Pattern {
	//P-one-EVENT embeds the arguments as a single  event in the stream ONCE
	//see P1bind for disclaimers.
	var <>pattern, <>event;

	*new { arg pattern, event;
		^super.newCopyArgs(pattern, event ?? { Event.default });
	}
	storeArgs { ^[pattern, event] }
	embedInStream { arg inval;
		var outval;
		outval = pattern.asStream.next(event);
		if (outval.isNil) { ^inval };
		inval = outval.yield;
		^inval;
	}
}
P1Rest {
	//P-one-Rest embeds the arguments as a single rest event in the stream ONCE
	//see P1bind for disclaimers.
	*new { arg dur;
		^Pfin(1, Rest(dur))
	}
}

PContext : Pattern {
	/* Looks up a key in an external state collection
	(
		~state = (a:1);
		~str =Pbind(\delta, PContext(~state, \a)).trace.play;
	)
	*/
	var <>state; //what to look up in
	var <>key; //which key to look up
	var <>default; //fallback to...
	*new { arg state, key, default;
		^super.newCopyArgs(state, key, default)
	}
	storeArgs { ^[state, key, default] }
	asStream {
		^FuncStream.new({state.at(key) ? default})
	}
}
PMarkovChain : Pattern {
	/* Ignores input; outputs a Markov sequence of 1st order,
	which is the only non-bullshit order.
	*/
	var <>probs; //transition matrix
	var <>halt; //stop value. defaults to nil, which never happens
	var <>state; //current/inital state
	var <states;
	*new { arg probs, halt, state=0;
		//normalise here?
		^super.newCopyArgs(
			probs.collect({|row| row.normalizeSum}),
			halt,
			state
		).initPMarkov;
	}
	//create random markov chain.
	//If i were a wanker, I might parameterise in terms of entropy rate.
	*random {
		arg nstates=4, disorder=0.25, ordertype=\static, halt, state=0;
		var order, probs;
		order = Array.series(nstates);
		ordertype.switch(
			\static, nil,
			\inc, {order = (order+1) % nstates},
			\chaos, {order = order.scramble},
			{"unknown ordertype '%'".format(ordertype.asString).throw}
		);
		probs = order.collect({
			arg dest, rownum;
			var disordered, ordered = 0.dup(nstates);
			ordered[dest] = 1;
			disordered = Array.rand(nstates, 0.0, 1.0);
			((disorder * disordered) + ((1-disorder) * ordered)).normalizeSum;
		});
		^this.new(probs, halt, state);
	}
	initPMarkov {
		states = Array.series(probs.size);
	}
	storeArgs { ^[probs, halt, state]}
	embedInStream { arg inval;
		//we more or less ignore the input value.
		({state != halt}).while({
			state = states.wchoose(probs[state]);
			inval = state.embedInStream(inval);
		});
		^inval;
	}
}
