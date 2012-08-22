/* I simulate uniform marginal variables from the stipulated 2d copula distribution
see http://www.math.uni-leipzig.de/~tschmidt/TSchmidt_Copulas.pdf
or, for exmpirical copulae, http://www.mathworks.com.au/products/statistics/examples.html?file=/products/demos/shipping/stats/copulademo.html#17

This turns out to be easiest for Gaussian, t-copulae and Marshall-Olkin, and
only somewhat easy for some Archimedeans - specifically, Frank, Gumbel and Clayton.
However, Archimedean copulae have a single coupling parameter, which is the whole
reason I'm interested in this technique, so I'd rather them. OTOH, for bivariate
coupling, it's not too crazy.
 */

///////////////////////////
//Archimedean copulae
///////////////////////////

//We define a 2d CDF using a specified generator.

~generators = (
	\clayton: (
		\forward: {|t, param=0| (1+t)**((-1/param).neg)},
		\inverse: {|t, param=0| ( t**(param.neg)) -1 },
		\ghat: {}
	)
);
~generators[\clayton][\forward].(0);
~generators[\clayton][\inverse].(0);
((0..16)/16).collect(~generators[\clayton][\inverse].(_, 0.5));
~generators[\clayton][\inverse].(0.5);