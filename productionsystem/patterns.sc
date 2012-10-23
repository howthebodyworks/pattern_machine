//Handy constructors for Patterns that I would like to be a little tidier.
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
Pob {
	//P-one-bind embeds the arguments as a single event in the stream ONCE
	//(events embed perpetually per default.)
	//note events with better defaults, or an event subclass,
	// might be able to avoid that
	*new { arg ... pairs;
		^Pfin(1, Pbind(*pairs))
	}
}