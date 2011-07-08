+ SequenceableCollection {
  indicesSuchThat {|fn|
    //Return list of indices matching fn. This is handy to .do things with later.
    ^this.collect({|item, i|
      (fn.value(item, i)).if(
        {i},
        {nil})
      }).select(
        {|item, i| item.isNil.not;}
    );
  }
}