function unavailable(name) {
  return () => {
    throw new Error(`Node fs.${name} is unavailable in the browser.`);
  };
}

export const openSync = unavailable("openSync");
export const closeSync = unavailable("closeSync");
export const readSync = unavailable("readSync");
export const writeSync = unavailable("writeSync");
export const unlinkSync = unavailable("unlinkSync");
export const rmdirSync = unavailable("rmdirSync");
export const renameSync = unavailable("renameSync");

export default {
  openSync,
  closeSync,
  readSync,
  writeSync,
  unlinkSync,
  rmdirSync,
  renameSync
};
