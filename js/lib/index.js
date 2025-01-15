// Export widget models and views, and the npm package version number.

export { RemoteFrameBufferModel, RemoteFrameBufferView } from './widget';

// export {version} from '../package.json'; -> yarn gives warning:

export const version = '0.4.4';  // updated by release.py
