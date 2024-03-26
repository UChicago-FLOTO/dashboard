var TimingComponent = {
  props: ["modelValue"],
  setup(props, ctx) {
    let on_demand_model = ref({
      "disable_add": true
    })
    let advanced_reservation_model = ref({
      "disable_add": true,
    })
    return {
      "types": [
        {
          "label": "On-demand",
          "value": "on_demand",
        },
        {
          "label": "In advance",
          "value": "advanced",
        },
      ],
      new_type: ref("on_demand"),
      on_demand_model, advanced_reservation_model,
      timings: props.modelValue,
      delete_item(str) {
        let index = props.modelValue.indexOf(str)
        if (index !== -1) {
          props.modelValue.splice(index, 1)
          ctx.emit('update:modelValue', props.modelValue)
        }
      },
      add_on_demand() {
        let str = `type=on_demand,days=${on_demand_model.value.days},hours=${on_demand_model.value.hours},minutes=${on_demand_model.value.minutes}`
        props.modelValue.push(str)
        ctx.emit('update:modelValue', props.modelValue)
      },
      add_advanced() {
        // Encode the date objects with the ISO timezone.
        let s = new Date(advanced_reservation_model.value.start).toISOString()
        let e = new Date(advanced_reservation_model.value.end).toISOString()
        let str = `type=advanced,start=${s},end=${e}`
        props.modelValue.push(str)
        ctx.emit('update:modelValue', props.modelValue)
      },
      expires_in_calculation: function () {
        let d = on_demand_model.value?.date
        on_demand_model.value.disable_add = true
        if (d) {
          let diff = Date.parse(d) - Date.now()
          if (diff > 0) {
            on_demand_model.value.disable_add = false

            on_demand_model.value.days = Math.floor(diff / 1000 / 60 / 60 / 24);
            diff -= on_demand_model.value.days * 1000 * 60 * 60 * 24

            on_demand_model.value.hours = Math.floor(diff / 1000 / 60 / 60);
            diff -= on_demand_model.value.hours * 1000 * 60 * 60

            on_demand_model.value.minutes = Math.floor(diff / 1000 / 60);
            diff -= on_demand_model.value.minutes * 1000 * 60

            return `Expires in ${on_demand_model.value.days} days, ${on_demand_model.value.hours} hours, ${on_demand_model.value.minutes} minutes.`
          } else {
            return "Date cannot be in the past."
          }
        } else {
          return "Expiration date not set."
        }
      },
      advanced_calculation: function () {
        advanced_reservation_model.value.disable_add = true
        let s = Date.parse(advanced_reservation_model.value?.start)
        let e = Date.parse(advanced_reservation_model.value?.end)
        if (s && e) {
          let diff = e - s
          // Check
          if (e < Date.now()) {
            return "End date can not be in the past."
          } else if (diff > 0) {
            advanced_reservation_model.value.disable_add = false
            let days = Math.floor(diff / 1000 / 60 / 60 / 24);
            diff -= days * 1000 * 60 * 60 * 24

            let hours = Math.floor(diff / 1000 / 60 / 60);
            diff -= hours * 1000 * 60 * 60

            let minutes = Math.floor(diff / 1000 / 60);
            diff -= minutes * 1000 * 60

            return `Runs for ${days} days, ${hours} hours, ${minutes} minutes, beginning on ${advanced_reservation_model.value?.start} local time.`
          } else {
            return "Start date must be before end date."
          }
        } else if (!s) {
          return "Start date not set."
        } else {
          return "End date not set"
        }
      }
    }
  },
  template: `
    <div class="q-pa-sm">
      <h5>Timings</h5>
      <q-card>
        <q-card-section>
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
        </q-card-section>

        <q-card-section>
          <h6>New timing</h6>

          <q-tabs v-model="new_type">
            <q-tab label="On-Demand" name="on_demand" />
            <q-tab label="In-Advance" name="advanced" />
          </q-tabs>

          <q-tab-panels v-model="new_type">
            <q-tab-panel name="on_demand">
              <p>
                You are adding an on-demand timing to this job. 
                This will run your application now until a given expiration time.
                Please choose the expiration below.
              </p>
              <div class="q-gutter-md row items-start">
                <q-input filled v-model="on_demand_model.date" label="End time">
                  <template v-slot:append>
                    <q-icon name="access_time" class="cursor-pointer">
                      <q-popup-proxy cover>
                        <div class="row q-gutter-md">
                          <div>
                            <q-date today-btn v-model="on_demand_model.date" mask="YYYY-MM-DD"></q-date>
                          </div>
                          <div>
                            <q-time now-btn v-model="on_demand_model.date" mask="YYYY-MM-DD HH:mm"></q-time>
                          </div>
                        </div>
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
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
            </q-tab-panel>         
            <q-tab-panel name="advanced">
              <p>
                You are adding an advance timing to this job. 
                This will run your application a given start time to an end time.
              </p>
              <div class="q-gutter-md row items-start">
                <q-input filled v-model="advanced_reservation_model.start" label="Start">
                  <template v-slot:append>
                    <q-icon name="access_time" class="cursor-pointer">
                      <q-popup-proxy cover>
                        <div class="row q-gutter-md">
                          <div>
                            <q-date today-btn v-model="advanced_reservation_model.start" mask="YYYY-MM-DD"></q-date>
                          </div>
                          <div>
                            <q-time now-btn v-model="advanced_reservation_model.start" mask="YYYY-MM-DD HH:mm"></q-time>
                          </div>
                        </div>
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
                <q-input filled v-model="advanced_reservation_model.end" label="End">
                  <template v-slot:append>
                    <q-icon name="access_time" class="cursor-pointer">
                      <q-popup-proxy cover>
                        <div class="row q-gutter-md">
                          <div>
                            <q-date today-btn v-model="advanced_reservation_model.end" mask="YYYY-MM-DD HH:mm"></q-date>
                          </div>
                          <div>
                            <q-time now-btn v-model="advanced_reservation_model.end" mask="YYYY-MM-DD HH:mm"></q-time>
                          </div>
                        </div>
                      </q-popup-proxy>
                    </q-icon>
                  </template>
                </q-input>
                <div>
                  <p>
                    {{ advanced_calculation() }}
                  </p>
                  <q-btn
                    color="primary"
                    icon-right="add"
                    @click="add_advanced()"
                    :disable="advanced_reservation_model.disable_add"
                  >Add</q-btn>
                </div>
              </div>
            </q-tab-panel>
          </q-tab-panels>
        </q-card-section>
      </q-card>
    </div>
    `
}
