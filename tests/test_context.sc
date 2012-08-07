TestPSContext : UnitTest {
	test_ContextContextApply {
		var left,right,target,combined,testnums;
		left = PSContext.newFrom((
			a: _*3,
			b: _*2
		));
		right = PSContext.newFrom((
			b: _+1,
			c: _*2
		));
		combined = left.applyTo(right);
		target = PSContext.newFrom((
			a: _*3,
			b: {|i| (i+1)*2},
			c: _*2	
		));
		testnums=[-1, 0, 0.1, 9.5];
		testnums.do({|n|
			[\a,\b,\c].do({|key|
				this.assertFloatEquals(
					combined.at(key).value(n),
					target.at(key).value(n),
					//"failure of Context-Context composition at key:\n\t" + key + "\nwith test input:\n\t"+n
				);
			});
		});
	}
	test_ContextEventApply {
		var left,right,target,combined;
		left = PSContext.newFrom((
			a: _*3,
			b: _+2
		));
		right = (
			b: 2.5,
			c: 3.25
		);
		combined = left.applyTo(right);
		target = PSContext.newFrom((
			b: 4.5,
			c: 3.25
		));
		[\a,\b,\c].do({|key|
			this.assertEquals(
				combined.at(key),
				target.at(key),
				//"failure of Context-Event composition at key:\n\t" + key + "\nwith test input:\n\t"+n
			);
		});
	}
}