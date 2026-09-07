export const RUN_STATES = Object.freeze({
  REQUESTED:'REQUESTED',
  UNDERSTOOD:'UNDERSTOOD',
  PLANNED:'PLANNED',
  EXECUTING:'EXECUTING',
  VERIFYING:'VERIFYING',
  DEPLOYING:'DEPLOYING',
  MEASURING:'MEASURING',
  COMPLETE:'COMPLETE',
  FAILED:'FAILED',
  DIAGNOSE:'DIAGNOSE',
  REPLAN:'REPLAN',
  RETRY:'RETRY',
  ROLLBACK:'ROLLBACK',
  WAITING_APPROVAL:'WAITING_APPROVAL'
});

const ALLOWED = {
  REQUESTED:['UNDERSTOOD','FAILED'],
  UNDERSTOOD:['PLANNED','FAILED'],
  PLANNED:['EXECUTING','WAITING_APPROVAL','FAILED'],
  EXECUTING:['VERIFYING','WAITING_APPROVAL','FAILED'],
  VERIFYING:['DEPLOYING','MEASURING','COMPLETE','FAILED'],
  DEPLOYING:['VERIFYING','MEASURING','FAILED'],
  MEASURING:['COMPLETE','REPLAN','FAILED'],
  FAILED:['DIAGNOSE','ROLLBACK'],
  DIAGNOSE:['REPLAN','RETRY','ROLLBACK'],
  REPLAN:['EXECUTING','WAITING_APPROVAL','FAILED'],
  RETRY:['EXECUTING','FAILED'],
  ROLLBACK:['VERIFYING','FAILED'],
  WAITING_APPROVAL:['EXECUTING','FAILED'],
  COMPLETE:[]
};

export function transition(run,next,meta={}){
  const current=run.state ?? RUN_STATES.REQUESTED;
  if(!(ALLOWED[current]||[]).includes(next)) throw new Error(`Invalid orchestrator transition ${current} -> ${next}`);
  return {
    ...run,
    state:next,
    updatedAt:new Date().toISOString(),
    history:[...(run.history||[]),{from:current,to:next,at:new Date().toISOString(),...meta}]
  };
}
