class FormationError(Exception): pass

class Formation(object):
    formations = ("4-4-2", "4-3-3", "3-5-2", "4-5-1", "3-4-3", "5-3-2")
    formation_labels = formations
    labels = ("Goalkeeper","Defender","Midfielder","Striker")
    fields = ("goalkeeper","defenders","midfielders","strikers")

    def __init__(self, formation):
        if formation not in self.formations:
            raise FormationError, "{0} is not an allowed formation".format(formation)
    
        self.__formation = [1]+[int(p) for p in formation.split("-")]
            
        if sum(self.__formation) != 11 or len(self.__formation) != 4:
            raise FormationError, "{0} is an invalid formation".format(self.__str__())

        self.__formation_name = formation
            
    def __str__(self):
        return self.__formation_name

    def __eq__(self, other):
        return self.__formation == other.__formation

    def __getitem__(self, item):
        if type(item) is int:
            number = item
            if not 0 <= number <= 10:
                raise IndexError, "{0} is an invalid player number".format(number)
            if number == 0: return self.labels[0]
            count=0    
            for i,p in enumerate(self.__formation):
                count+=p
                if number+1 <= count: return self.labels[i]
        elif type(item) is str:
            position = item
            if position not in self.fields:
                raise KeyError, "{0} is an invalid position".format(position)
            return self.__formation[self.fields.index(position)]

    def __iter__(self):
        return iter(self.__formation)

    def __sub__(self, other):
        return [p1-p2 for p1,p2 in zip(self,other)]
        
    def list(self):
        return self.__formation
        
if __name__ == "__main__":
    for f in Formation.formations:
        formation = Formation(f)
        print("{0}: {1}".format(formation, formation.list()))
        print formation[5]