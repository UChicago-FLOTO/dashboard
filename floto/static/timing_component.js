var TimingComponent = {
  props: ["modelValue"],
  setup(props, ctx) {
    let on_demand_model = reactive({
      "disable_add": true
    })
    return { 
      "types": [
        {
          "label": "On-demand",
          "value": "on_demand",
        },
      ],
      new_type: ref("on_demand"),
      on_demand_model,
      timings: props.modelValue,
      delete_item(str){
        let index = props.modelValue.indexOf(str)
        if (index !== -1){
          props.modelValue.splice(index, 1)
          ctx.emit('update:modelValue', props.modelValue)
        }
      },
      add_on_demand(){
        let str = `type=on_demand,days=${on_demand_model.days},hours=${on_demand_model.hours},minutes=${on_demand_model.minutes}`
        props.modelValue.push(str)
        ctx.emit('update:modelValue', props.modelValue)
      },
      expires_in_calculation: function(){
        let d = on_demand_model?.date
        let t = on_demand_model?.time
        on_demand_model.disable_add = true
        if (d && t) {
          let diff = Date.parse(`${d} ${t}`) - Date.now()
          if (diff > 0){
            on_demand_model.disable_add = false

            on_demand_model.days = Math.floor(diff / 1000 / 60 / 60 / 24);
            diff -= on_demand_model.days * 1000 * 60 * 60 * 24

            on_demand_model.hours = Math.floor(diff / 1000 / 60 / 60 );
            diff -= on_demand_model.hours * 1000 * 60 * 60

            on_demand_model.minutes = Math.floor(diff / 1000 / 60 );
            diff -= on_demand_model.minutes * 1000 * 60

            return `Expires in ${on_demand_model.days} days, ${on_demand_model.hours} hours, ${on_demand_model.minutes} minutes.`
          } else {
            return "Date cannot be in the past."
          }
        } else if (!t) {
          return "Expiration time not set."
        } else {
          return "Expiration date not set."
        }
      },
    }
  },
  template: `
    <div class="q-pa-sm">
      <h5>Timings</h5>
      <q-field
        v-model="timings"
        :rules="[ val => val && val.length >= 1 || 'Please add at least one timing from below.']"
      >
        <template v-slot:control>
          <ul>
            <li v-for="s in timings">
              {{ s }} 
              <q-btn
                color="negative"
                icon-right="delete"
                no-caps
                flat
                dense
                @click="delete_item(s)"
              />
            </li>
            <li v-if="timings.length === 0">This job is never scheduled to run!</li>
          </ul>
        </template>
      </q-field>
      <h6>New timing</h6>
      <q-select
      filled
        v-model="new_type"
        :options="types"
      >
      </q-select>
      <q-card v-if="new_type == 'on_demand'">
        <q-card-section>
          <p>
            You are adding an on-demand timing to this job. 
            This will run your application now until a given expiration time.
            Please choose the expiration below.
          </p>
          <div class="row justify-between">
            <q-date
              v-model="on_demand_model.date"
              today-btn
            />
            <q-time 
              v-model="on_demand_model.time"
              mask="hh:mm A" 
              now-btn
            />
            <div>
              <p>
                {{ expires_in_calculation() }}
              </p>
              <q-btn
                color="primary"
                icon-right="add"
                @click="add_on_demand(s)"
                :disable="on_demand_model.disable_add"
              >Add</q-btn>
            </div>
            
          </div>          
        </q-card-section>
      </q-card>
    </div>
    `
}
  