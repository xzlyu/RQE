import queue

from RuleBased.Params import ht_conn


class SparqlParser:
    def __init__(self, sparql):
        self.sparql = sparql
        self.var2entity = {}
        self.r_name_list = []
        '''[var1,var2,var3], sorted by alphabet order'''
        self.var_list = []
        '''
        list of BGP which has two variable
        key: token => h,t, h and t are sorted by alphabet order
        value: list of splited BGP => [[h,r,t],[h,r,t],....] 
        '''
        self.var2BGP = {}

        '''
        list of BGP which has one variable
        key: h or t, it depends on which is varible
        value: list of splited BGP => [[h,r,t],[h,r,t],...]
        '''
        self.var1BGP = {}

        '''
        [
            [
                [var1],[var2],[var3]
            ],
            [
                [var1],[var2],[var3]
            ],
            ....
        ]
        '''
        self.res = []
        self.temp_res = []

    def parse_sparql(self):
        body_start_index = self.sparql.find("{")
        body_end_index = self.sparql.find("}")
        body = self.sparql[body_start_index + 1:body_end_index].strip()
        for BGP in body.split("\n"):
            BGP = BGP.strip().strip(".")
            head, relation, tail = BGP.split()
            self.r_name_list.append(relation)
            if head.startswith('?') and tail.startswith("?"):
                token = ht_conn.join([head, tail])
                if token not in self.var2BGP:
                    self.var2BGP[token] = []
                self.var2BGP[token].append([head, relation, tail])
            elif head.startswith("?") and not tail.startswith("?"):
                if head not in self.var1BGP:
                    self.var1BGP[head] = []
                self.var1BGP[head].append([head, relation, tail])
            elif not head.startswith("?") and tail.startswith("?"):
                if tail not in self.var1BGP:
                    self.var1BGP[tail] = []
                self.var1BGP[tail].append([head, relation, tail])
            if head.startswith("?"):
                self.var_list.append(head)
            if tail.startswith("?"):
                self.var_list.append(tail)
        self.r_name_list = list(set(self.r_name_list))
        self.var_list = list(set(self.var_list))
        self.var_list.sort()

        for var in self.var_list:
            self.var2entity[var] = set()
            self.temp_res.append([])

    '''
    Update results searched. This is used for BGP with 2 variables.
    Parameters:
    -----------
    h_var: string, name of head variable
    t_var: string, name of tail variable
    passed_ht_list: list, list of passed ht, [[h,t],[h,t],...]
    passed_ht_token_set: set, set of tokens of passed ht, token => h,t
    
    Returns:
    -----------
    None
    Update self.var2entity[h_var], self.var2entity[t_var] and res.
    '''

    def update_res_var2entity(self, h_var, t_var, passed_ht_list, passed_ht_token_set):
        h_res_idx = sp.var_list.index(h_var)
        t_res_idx = sp.var_list.index(t_var)
        h_set = set()
        t_set = set()

        if len(self.res) == 0:
            for ht in passed_ht_list:
                copy_res = self.temp_res
                copy_res[h_res_idx] = [ht[0]]
                copy_res[t_res_idx] = [ht[-1]]
                self.res.append(copy_res)
                h_set.add(ht[0])
                t_set.add(ht[-1])
        else:
            temp_store = []
            for one_res in self.res:
                h = one_res[h_res_idx][0]
                t = one_res[t_res_idx][0]
                if ht_conn.join([h, t]) in passed_ht_token_set:
                    temp_store.append(one_res)
                    h_set.add(h)
                    t_set.add(t)
            self.res = temp_store

        self.var2entity[h_var] = h_set
        self.var2entity[t_var] = t_set

    '''
    Get candidates of var_name
    Parameters:
    -----------
    var_name: string, for example, ?p
    the name of variable
    
    Returns:
    out: list
    list of candidates of var_name
    '''

    def get_candidate_by_var(self, var_name):
        return self.var2entity[var_name]

    def execute_var1BGP(self, r_rules_dict, graph):
        for var in self.var1BGP:
            for BGP in self.var1BGP[var]:
                if BGP[0].startswith("?"):
                    h_idx_list = []
                    t_idx_list = [graph.e2idx[BGP[2]]]
                    tar_var = BGP[0]
                    idx_of_var = 0
                else:
                    h_idx_list = [graph.e2idx[BGP[0]]]
                    t_idx_list = []
                    tar_var = BGP[2]
                    idx_of_var = 1

                rule_path_list=[[graph.r2idx[BGP[1]]]]
                rule_path_list.extend([rule_obj.r_path for rule_obj in r_rules_dict[graph.r2idx[BGP[1]]]])

                passed_ht = []

                for rule_path in rule_path_list:
                    temp_passed_ht, temp_passed_ht_token = graph.get_passed_ht_from_one_end(h_idx_list, t_idx_list,
                                                                                            rule_path)
                    passed_ht.extend(temp_passed_ht)

                if len(self.var2entity[tar_var]) == 0:
                    temp_res = set()
                    for ht in passed_ht:
                        temp_res.add(ht[idx_of_var])
                    self.var2entity[tar_var] = temp_res
                else:
                    temp_res = set()
                    for ht in passed_ht:
                        temp_res.add(ht[idx_of_var])
                    self.var2entity[tar_var] = temp_res & self.var2entity[tar_var]

    def execute_var2BGP(self, r_rules_dict, graph):
        BGP_queue = queue.Queue()
        for token in self.var2BGP:
            BGP_queue.put(token)
        while not BGP_queue.empty():
            token = BGP_queue.get()
            h_var, r_name, t_var = self.var2BGP[token]
            h_idx_list = list(self.var2entity[h_var])
            t_idx_list = list(self.var2entity[t_var])

            rule_list = r_rules_dict[graph.r2idx[r_name]]
            rule_list.append([graph.r2idx[r_name]])

            if len(h_idx_list) == 0 and len(t_idx_list) == 0:
                BGP_queue.put(token)
                print("size of h_idx_list and size of t_idx_list are zero.")
                continue

            if len(h_idx_list) == 0 or len(t_idx_list) == 0:
                passed_ht_token_set = set()
                for rule in rule_list:
                    temp_passed_ht, temp_passed_token = graph.get_passed_ht_from_one_end(h_idx_list, t_idx_list, rule)
                    passed_ht_token_set = passed_ht_token_set | temp_passed_ht

                passed_ht = [ht_token.split(ht_conn) for ht_token in passed_ht_token_set]
                self.update_res_var2entity(h_var, t_var, passed_ht, passed_ht_token_set)
            else:
                passed_ht_list, passed_ht_token_set = graph.pass_verify(h_idx_list, t_idx_list, rule_list)
                self.update_res_var2entity(h_var, t_var, passed_ht_list, passed_ht_token_set)


if __name__ == "__main__":
    sparql = """
    SELECT ?film WHERE{
        ?film <http://dbpedia.org/ontology/director> ?p.
        ?film <http://dbpedia.org/ontology/starring> ?p.
        ?p <http://dbpedia.org/ontology/birthPlace> <http://dbpedia.org/resource/North_America>.
    }
    """

    sp = SparqlParser(sparql=sparql)
    sp.parse_sparql()