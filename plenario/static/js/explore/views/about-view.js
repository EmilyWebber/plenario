var AboutView = Backbone.View.extend({
    events: {
        'click .detail': 'detailView'
    },
    initialize: function(){
        this.render();
    },
    render: function(){
        $('#list-view').show();
        $('#detail-view').hide();
        this.$el.empty();
        this.$el.spin('large');
        var self = this;
        $.when(this.get_datasets()).then(
            function(resp){
                self.$el.spin(false);
                self.$el.html(template_cache('aboutTemplate', {datasets:resp}));
                var dataObjs = {}
                // console.log(resp);
                $.each(resp, function(i, obj){
                    dataObjs[obj['dataset_name']] = obj;
                })
                self.datasetsObj = dataObjs;

                $('#available-datasets').DataTable( {
                    "aaSorting": [ [0,'asc'] ],
                    "aoColumns": [
                        null,
                        null,
                        { "bSortable": false }
                    ],
                    "paging": false,
                    "searching": false,
                    "info": false
                } );
            }
        )
    },
    get_datasets: function(){
        return $.ajax({
            url: '/api/',
            dataType: 'json'
        })
    },
    detailView: function(e){

        var query = {};
        var start = $('#start-date-filter').val();
        var end = $('#end-date-filter').val();
        start = moment(start);
        if (!start){ start = moment().subtract('days', 180); }
        end = moment(end)
        if(!end){ end = moment(); }
        start = start.startOf('day').format('YYYY/MM/DD');
        end = end.endOf('day').format('YYYY/MM/DD');

        query['obs_date__le'] = end;
        query['obs_date__ge'] = start;
        query['agg'] = $('#time-agg-filter').val();

        var dataset_name = $(e.target).data('dataset_name')
        // console.log(dataset_name);
        query['dataset_name'] = dataset_name

        $('#map-view').empty();
        new DetailView({el: '#map-view', attributes: {query: query, meta: this.datasetsObj[dataset_name]}})
        var route = 'detail/' + $.param(query)
        router.navigate(route)
    }
});