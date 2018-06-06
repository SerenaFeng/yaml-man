a = {
    'struct': {
        'inner1':1,
         'inner2': {
             'inner21':21,
             'inner22':{
                 'inner221':221,
                 'inner222':222
             }
         }
    },
    'name': 'yamlman',
}

print a.items()
k,v = next(iter(a.items()))
print k
print v